<template lang="pug">
div(v-resize:throttle="onResize")
  div(ref="chart")
  span(style="display: none") {{ update }}
</template>

<script>
import c3 from 'c3';
import { select } from 'd3-selection';
import { deviation, mean } from 'd3-array';
import { format } from 'd3-format';
import resize from 'vue-resize-directive';

import 'c3/c3.css';
import './score-plot.css';

// This function uses C3's `done` API to return a promise that can be awaited,
// averting the need to place the continuation of the function it's embedded in
// into the done callback.
function c3LoadWait(chart, opts) {
  return new Promise((resolve) => {
    chart.load({
      ...opts,
      done: () => resolve(),
    });
  });
}

function sameContents(a, b) {
  if (a.length !== b.length) {
    return false;
  }

  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return false;
    }
  }

  return true;
}

function fixCSS(id) {
  // replace non css stuff to _
  return id.replace(/[\s!#$%&'()*+,./:;<=>?@[\\\]^`{|}~]+/g, '_');
}

function covar(xs, ys) {
  const e_xy = mean(xs.map((x, i) => x * ys[i]));
  const e_xx = mean(xs);
  const e_yy = mean(ys);

  return e_xy - e_xx * e_yy;
}

// Create a plot of the covariance confidence ellipse of `x` and `y`.
// x, y : array_like, shape (n, )
//     Input data.
// std : float
//     The number of standard deviations to determine the ellipse's radiuses.
//
// Port of Python function from:
//      https://matplotlib.org/gallery/statistics/confidence_ellipse.html
function confidenceEllipse(x, y, std, xScale, yScale) {
  if (x.length < 2 || y.length < 2) {
    // cannot generate an ellipse for less than two data points
    return { rx: 0, ry: 0, transform: '' };
  }
  // cov = np.cov(x, y)
  const xdev = deviation(x);
  const ydev = deviation(y);
  const xcov = xdev * xdev;
  const ycov = ydev * ydev;
  const xycov = covar(x, y);

  // pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
  const pearson = xycov / Math.sqrt(xcov * ycov);

  // # Using a special case to obtain the eigenvalues of this
  // # two-dimensionl dataset.
  // ell_radius_x = np.sqrt(1 + pearson)
  // ell_radius_y = np.sqrt(1 - pearson)
  const ell_radius_x = Math.sqrt(1 + pearson);
  const ell_radius_y = Math.sqrt(1 - pearson);

  // # Calculating the stdandard deviation of x from
  // # the squareroot of the variance and multiplying
  // # with the given number of standard deviations.
  // scale_x = np.sqrt(cov[0, 0]) * n_std
  // mean_x = np.mean(x)
  const scale_x = Math.sqrt(xcov) * std;
  const mean_x = mean(x);

  // # calculating the stdandard deviation of y ...
  // scale_y = np.sqrt(cov[1, 1]) * n_std
  // mean_y = np.mean(y)
  const scale_y = Math.sqrt(ycov) * std;
  const mean_y = mean(y);

  // transf = transforms.Affine2D() \
  //     .rotate_deg(45) \
  //     .scale(scale_x, scale_y) \
  //     .translate(mean_x, mean_y)
  const transform = `translate(${xScale(mean_x)} ${yScale(mean_y)}) scale(${xScale(scale_x) - xScale(0)} ${yScale(scale_y) - yScale(0)}) rotate(45)`;

  return {
    rx: ell_radius_x,
    ry: ell_radius_y,
    transform,
  };
}

export default {
  directives: {
    resize,
  },
  props: {
    pcX: {
      required: true,
      type: Number,
      validator: Number.isInteger,
    },
    pcY: {
      required: true,
      type: Number,
      validator: Number.isInteger,
    },
    showEllipses: {
      type: Boolean,
      default: true,
    },
    pcCoords: {
      required: true,
      type: Array,
      validator: (prop) => prop.every((coord) => coord.every(Number.isFinite)),
    },
    rowLabels: {
      required: true,
      type: Array,
      validator: (prop) => prop.every((val) => typeof val !== 'object'),
    },
    colors: {
      required: true,
      type: Array,
      validator: (prop) => prop.every((val) => ['name', 'color'].every((key) => Object.prototype.hasOwnProperty.call(val, key))),
    },
    groupLabels: {
      required: true,
      type: Object,
    },
    eigenvalues: {
      required: true,
      type: Array,
      validator: (prop) => prop.every(Number.isFinite),
    },
    columns: {
      required: true,
      type: Array,
      validator: (prop) => prop.every((column) => ['column_header', 'column_type'].every((key) => Object.prototype.hasOwnProperty.call(column, key))),
    },
  },

  data() {
    return {
      chart: null,
      ellipseVisible: {},
      labels: {},
      duration: 500,
      width: 100,
      height: 100,
    };
  },

  computed: {
    pcPoints() {
      const {
        pcCoords,
        pcX,
        pcY,
      } = this;

      const x = pcCoords.map((p) => p[pcX - 1]);
      const y = pcCoords.map((p) => p[pcY - 1]);

      return [x, y];
    },

    totalVariance() {
      const {
        eigenvalues,
      } = this;

      return eigenvalues.reduce((acc, x) => acc + x, 0);
    },

    pcVariances() {
      const {
        pcX,
        pcY,
        eigenvalues,
        totalVariance,
      } = this;

      return [
        eigenvalues[pcX - 1] / totalVariance,
        eigenvalues[pcY - 1] / totalVariance,
      ];
    },

    group() {
      const { columns } = this;
      const column = columns.find((elem) => elem.column_type === 'group');

      return column.column_header;
    },

    colorMapping() {
      const {
        colors,
      } = this;

      const mapping = {};
      colors.forEach((color) => {
        mapping[color.name] = color.color;
      });

      return mapping;
    },

    valid() {
      const {
        pcCoords,
        rowLabels,
        groupLabels,
        eigenvalues,
      } = this;

      return pcCoords.length > 0
        && rowLabels.length > 0
        && Object.keys(groupLabels).length > 0
        && eigenvalues.length > 0;
    },

    updateDeps() {
      const {
        colorMapping,
        pcPoints,
        pcX,
        pcY,
        showEllipses,
        ellipseVisible,
        duration,
        pcVariances,
        valid,
        width,
        height,
      } = this;

      return {
        colorMapping,
        pcPoints,
        pcX,
        pcY,
        showEllipses,
        ellipseVisible,
        duration,
        pcVariances,
        valid,
        width,
        height,
      };
    },
  },

  watch: {
    updateDeps() {
      this.update();
    },
  },

  mounted() {
    this.chart = c3.generate({
      bindto: this.$refs.chart,
      data: {
        columns: [],
        type: 'scatter',
      },
      axis: {
        x: {
          label: {
            text: 'x',
            position: 'outer-center',
          },
          tick: {
            fit: false,
          },
        },
        y: {
          label: {
            text: 'y',
            position: 'outer-middle',
          },
        },
      },
      legend: {
        item: {
          onmouseover: (id) => {
            this.chart.focus(id);
            this.focusEllipse(id);
          },

          onmouseout: () => {
            this.chart.focus();
            this.focusEllipse();
          },

          onclick: (id) => {
            this.chart.toggle(id);
            const showing = this.toggleEllipse(id);

            if (!showing) {
              this.chart.focus();
              this.focusEllipse();
            }
          },
        },
      },
      tooltip: {
        contents: (d, title, value, color) => {
          const category = d[0].id;
          const label = this.labels[category][d[0].index];
          const col = color(category);
          const fmt = format('.2f');
          const x = fmt(d[0].x);
          const y = fmt(d[0].value);

          const html = `
          <div class="c3-tooltip-container">
            <table class="c3-tooltip">
              <tbody>
                <tr>
                  <th colspan="2">${label}</th>
                </tr>
                <tr class="c3-tooltip-name--${category}">
                  <td class="name">
                    <span style="background-color:${col}"></span>
                    ${category}
                  </td>
                  <td class="value">(${x}, ${y})</td>
                </tr>
              </tbody>
            </table>
          </div>`;

          return html;
        },
      },
    });

    select(this.$refs.chart)
      .select('.c3-chart')
      .append('g')
      .classed('c3-custom-ellipses', true);
  },

  methods: {
    grouped(xdata, ydata) {
      const {
        groupLabels,
        rowLabels,
        group,
      } = this;

      const grouped = {};

      xdata.forEach((d, i) => {
        const g = groupLabels[group][i];

        if (!Object.prototype.hasOwnProperty.call(grouped, g)) {
          grouped[g] = [];
        }

        grouped[g].push({
          x: d,
          y: ydata[i],
          label: rowLabels[i],
        });
      });

      Object.keys(grouped).forEach((g) => {
        grouped[g].sort((a, b) => a.x - b.x);
      });

      return grouped;
    },

    focusEllipse(which) {
      const selector = which ? `ellipse.ellipse-${fixCSS(which)}` : 'ellipse.ellipse';

      this.defocusEllipse();

      select(this.$refs.chart)
        .selectAll(selector)
        .style('opacity', 1.0);
    },

    defocusEllipse(which) {
      const selector = which ? `ellipse.ellipse-${fixCSS(which)}` : 'ellipse.ellipse';

      select(this.$refs.chart)
        .selectAll(selector)
        .style('opacity', 0.3);
    },

    toggleEllipse(which) {
      this.ellipseVisible[which] = !this.ellipseVisible[which];
      this.update();
      return this.ellipseVisible[which];
    },

    onResize() {
      const bb = this.$el.getBoundingClientRect();
      this.width = bb.width - 20;
      this.height = bb.height;
    },

    async update() {
      const {
        colorMapping,
        pcPoints,
        pcX,
        pcY,
        showEllipses,
        ellipseVisible,
        duration,
        pcVariances,
        valid,
        width,
        height,
      } = this.updateDeps;

      if (!valid) {
        return;
      }

      const [xData, yData] = pcPoints;
      if (xData.includes(undefined) || yData.includes(undefined)) {
        // undefined data indicates an out of bounds pcX or pcY
        // no point in trying to render invalid data
        return;
      }

      const fmt = format('.2%');
      const x = `PC${pcX} (${fmt(pcVariances[0])})`;
      const y = `PC${pcY} (${fmt(pcVariances[1])})`;

      this.chart.axis.labels({
        x,
        y,
      });

      this.chart.resize({
        width,
        height,
      });

      const grouped = this.grouped(xData, yData);

      const groups = Object.keys(grouped);
      const columns = [];
      const labels = {};
      const xs = {};
      groups.forEach((g) => {
        const xName = `${g}_x`;

        columns.push([xName, ...grouped[g].map((d) => d.x)]);
        columns.push([g, ...grouped[g].map((d) => d.y)]);

        labels[g] = [...grouped[g].map((d) => d.label)];

        xs[g] = xName;
      });

      this.labels = labels;

      // Collect the existing and incoming column names.
      const oldCols = this.chart.data().map((d) => d.id);
      const newCols = columns.map((d) => d[0])
        .filter((d) => !d.endsWith('_x'));

      // Draw the C3 chart, unloading the existing data first if the column names
      // have changed.
      await c3LoadWait(this.chart, {
        columns,
        xs,
        unload: !sameContents(oldCols, newCols),
      });

      // Set the colors.
      this.chart.data.colors(colorMapping);

      // Draw the data ellipses.
      const scaleX = this.chart.internal.x;
      const scaleY = this.chart.internal.y;
      const cmap = this.chart.internal.color;

      const confidenceEllipses = Object.keys(grouped).map((group) => {
        const groupx = grouped[group].map((d) => d.x);
        const groupy = grouped[group].map((d) => d.y);

        return {
          ...confidenceEllipse(groupx, groupy, 1, scaleX, scaleY),
          category: group,
        };
      });

      confidenceEllipses.forEach((ell) => {
        if (ellipseVisible[ell.category] === undefined) {
          ellipseVisible[ell.category] = true;
        }
      });

      select(this.$refs.chart)
        .select('.c3-custom-ellipses')
        .selectAll('ellipse')
        .data(confidenceEllipses)
        .join(
          (enter) => enter
            .append('ellipse')
            .attr('class', (d) => `ellipse-${fixCSS(d.category)}`)
            .classed('ellipse', true)
            .style('fill', 'none')
            .style('stroke', (d) => cmap(d.category))
            .style('stroke-width', 1)
            .attr('vector-effect', 'non-scaling-stroke')
            .attr('rx', (d) => d.rx)
            .attr('ry', (d) => d.ry)
            .attr('transform', (d) => d.transform)
            .style('opacity', 1),
          (update) => update
            .attr('class', (d) => `ellipse-${fixCSS(d.category)}`)
            .classed('ellipse', true)
            .style('display', (d) => (showEllipses && ellipseVisible[d.category] ? null : 'none'))
            .transition()
            .duration(300)
            .attr('rx', (d) => d.rx)
            .attr('ry', (d) => d.ry)
            .attr('transform', (d) => d.transform),
          (exit) => exit.transition('exit')
            .duration(duration)
            .style('opacity', 0)
            .remove(),
        );
    },
  },
};
</script>
