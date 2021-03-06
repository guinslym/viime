<script>
import RocCurve from './RocCurve.vue';
import VisTileLarge from './VisTileLarge.vue';
import { CSVService } from '../../common/api.service';
import plotData from './mixins/plotData';

export default {
  components: {
    VisTileLarge,
    RocCurve,
  },

  mixins: [plotData('roc')],

  props: {
    id: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      metabolites: [], // currently selected metabolites
      group1: '',
      group2: '',
      metaboliteSource: 'all',
      method: 'random_forest',
      methodOptions: [
        { value: 'random_forest', text: 'Random Forest' },
        { value: 'logistic_regression', text: 'Logistic Regression' },
      ],
      pcaData: null, // data from factor analysis endpoint
      threshold: 0.4, // threshold for factor analysis
    };
  },
  computed: {
    // Column names (i.e. metabolites) available for selection,
    // filtered based on current metabolite source
    columns() {
      if (this.metaboliteSource === 'all') {
        return this.dataset.column.data.filter((column) => column.column_type === 'measurement')
          .map((column) => column.column_header);
      }
      if (this.metaboliteSource === 'selected') {
        return this.dataset.selectedColumns;
      }
      const { metabolites } = this.pcaData;
      if (!metabolites) {
        return [];
      }
      return metabolites.filter((m, i) => (this.pcaData.factor[i] === this.metaboliteSource));
    },
    groups() {
      return this.dataset.groupLevels.map((level) => level.name);
    },
    metaboliteSourceOptions() {
      let options = [
        { value: 'all', text: 'All metabolites' },
        { value: 'selected', text: 'Selected Metabolites' },
      ];
      if (this?.pcaData?.factor) {
        options = options.concat(this.pcaData.factor.map((factor) => ({ value: factor, text: `PC${factor}` })));
      }
      return options;
    },
    sensitivities() {
      if (!this.plot.data || !this.group1 || !this.group2 || this.metabolites.length === 0) {
        return [];
      }
      return this.plot.data.sensitivities;
    },
    specificities() {
      if (!this.plot.data || !this.group1 || !this.group2 || this.metabolites.length === 0) {
        return [];
      }
      return this.plot.data.specificities;
    },
    auc() {
      if (!this.plot.data || !this.group1 || !this.group2 || this.metabolites.length === 0) {
        return 0;
      }
      return this.plot.data.auc[0];
    },
  },
  watch: {
    // get new factor analysis when threshold changes
    threshold() {
      this.getFactors();
      this.metaboliteSource = 'all';
    },

    // Clear metabolites when metabolite source is changed to 'All'
    // If the source is changed to 'Selected' or one of the PC factors,
    // populate the list with the filtered metabolite and graph them.
    metaboliteSource(newSource) {
      this.metabolites = newSource === 'all' ? [] : this.columns;
      this.changePlotArgs({ columns: JSON.stringify(this.metabolites) });
    },

    // These two watchers prevent the same group from being selected twice.
    group1(newGroup, oldGroup) {
      this.changePlotArgs({ group1: newGroup });
      if (this.group2 === newGroup) {
        this.group2 = oldGroup;
        this.changePlotArgs({ group2: oldGroup });
      }
    },
    group2(newGroup, oldGroup) {
      this.changePlotArgs({ group2: newGroup });
      if (this.group1 === newGroup) {
        this.group1 = oldGroup;
        this.changePlotArgs({ group1: oldGroup });
      }
    },
  },
  mounted() {
    // Perform an initial factor analysis when component is mounted
    this.getFactors();
  },
  methods: {
    // Called when a metabolite is removed from the ROC analysis
    // as a result of the user clicking the red 'X' next to its
    // name in the 'Metabolites' autoselect
    removeMetabolite(metabolite) {
      this.metabolites.splice(this.metabolites.indexOf(metabolite), 1);
      this.changePlotArgs({ columns: JSON.stringify(this.metabolites) });
    },
    async getFactors() {
      if (this.metaboliteSourceOptions.length > 2) {
        this.metaboliteSourceOptions.splice(2, this.metaboliteSourceOptions.length - 2);
      }
      try {
        // perform factor analysis
        const pcaDataResponse = await CSVService.getAnalysis(this.dataset.id, 'factors', { threshold: this.threshold });
        this.pcaData = pcaDataResponse?.data?.metabolites ? pcaDataResponse.data : null;
      } catch (err) {
        this.pcaData = null;
      }
    },
  },
};
</script>

<template>
  <vis-tile-large
    v-if="plot"
    title="Group Prediction"
    :loading="plot.loading"
    expanded="expanded"
    download
  >
    <template #controls>
      <v-toolbar
        class="darken-3"
        color="primary"
        dark="dark"
        flat="flat"
        dense="dense"
        :card="false"
      >
        <v-toolbar-title>Metabolite Source</v-toolbar-title>
      </v-toolbar>
      <v-card
        class="mx-3 px-2"
        flat="flat"
      >
        <v-select
          v-model="metaboliteSource"
          class="py-2"
          hide-details="hide-details"
          :items="metaboliteSourceOptions"
        />
      </v-card>
      <v-toolbar
        class="darken-3"
        color="primary"
        dark="dark"
        flat="flat"
        dense="dense"
        :card="false"
      >
        <v-toolbar-title>
          Loading Threshold
          <v-tooltip
            v-if="!pcaData"
            slot="append"
            right
          >
            <v-icon
              slot="activator"
              color="error"
            >
              {{ $vuetify.icons.warningCircle }}
            </v-icon>
            <span>
              Factor analysis with loading threshold of <br>
              {{ threshold }} returned 0 metabolites.
            </span>
          </v-tooltip>
        </v-toolbar-title>
      </v-toolbar>
      <v-card
        class="mx-3"
        flat="flat"
      >
        <v-card-actions>
          <v-layout column="column">
            <v-slider
              class="my-1 minCorrelation"
              :value="threshold"
              label="0"
              thumb-label="always"
              hide-details="hide-details"
              min="0"
              max="1"
              step="0.1"
              style="padding-top: 16px;"
              @change="threshold = $event"
            />
          </v-layout>
        </v-card-actions>
      </v-card>
      <v-toolbar
        class="darken-3"
        color="primary"
        dark="dark"
        flat="flat"
        dense="dense"
        :card="false"
      >
        <v-toolbar-title>Metabolites</v-toolbar-title>
      </v-toolbar>
      <v-card
        class="mx-3 px-1"
        flat="flat"
      >
        <v-autocomplete
          v-model="metabolites"
          :items="columns"
          chips="chips"
          dense="dense"
          multiple
          clearable
          deletable-chips="deletable-chips"
          auto-select-first="auto-select-first"
          hide-selected="hide-selected"
          hide-details="hide-details"
          @change="changePlotArgs({columns: JSON.stringify(metabolites)})"
        >
          <template v-slot:selection="data">
            <v-tooltip right="right">
              <template v-slot:activator="{ on }">
                <v-chip
                  small="small"
                  v-on="on"
                >
                  <v-icon
                    class="closePillButton pr-1"
                    small="small"
                    @click.stop="removeMetabolite(data.item)"
                  >
                    mdi-close
                  </v-icon><span class="searchResult">{{ data.item }}</span>
                </v-chip>
              </template><span>{{ data.item }}</span>
            </v-tooltip>
          </template>
        </v-autocomplete>
      </v-card>
      <v-toolbar
        class="darken-3"
        color="primary"
        dark="dark"
        flat="flat"
        dense="dense"
        :card="false"
      >
        <v-toolbar-title>Group 1</v-toolbar-title>
      </v-toolbar>
      <v-card
        class="mx-3 px-2"
        flat="flat"
      >
        <v-select
          v-model="group1"
          class="py-2"
          hide-details="hide-details"
          :items="groups"
        />
      </v-card>
      <v-toolbar
        class="darken-3"
        color="primary"
        dark="dark"
        flat="flat"
        dense="dense"
        :card="false"
      >
        <v-toolbar-title>Group 2</v-toolbar-title>
      </v-toolbar>
      <v-card
        class="mx-3 px-2"
        flat="flat"
      >
        <v-select
          v-model="group2"
          class="py-2"
          hide-details="hide-details"
          :items="groups"
        />
      </v-card>
      <v-toolbar
        class="darken-3"
        color="primary"
        dark="dark"
        flat="flat"
        dense="dense"
        :card="false"
      >
        <v-toolbar-title>Method</v-toolbar-title>
      </v-toolbar>
      <v-card
        class="mx-3 px-2"
        flat="flat"
      >
        <v-select
          v-model="method"
          class="py-2"
          hide-details="hide-details"
          :items="methodOptions"
          @change="changePlotArgs({method: $event})"
        />
      </v-card>
    </template>
    <roc-curve
      :specificities="specificities"
      :sensitivities="sensitivities"
      :auc="auc"
    />
  </vis-tile-large>
</template>

<style>
.closePillButton:hover {
  color: red;
}

.searchResult {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  width: 100px;
}
</style>
