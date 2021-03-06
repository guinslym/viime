<script>
import ColorerOption from './ColorerOption.vue';
import metaboliteMixin from './mixins/metaboliteMixin';
import { colors } from '../../utils/constants';

export default {
  components: {
    ColorerOption,
  },
  mixins: [metaboliteMixin],
  props: {
    title: {
      type: String,
      required: false,
      default: 'Metabolite Color',
    },
    value: { // {option: string | null,
    // levels: {name: string, color: string}[], apply(row: string) => string | null}
      type: Object,
      required: false,
      default: null,
    },
  },
  computed: {
    validatedValue() {
      if (this.value) {
        return this.value.option;
      }
      if (this.options.length === 0) {
        return null;
      }
      const v = this.options[0].value;
      this.changeValue(v);
      return v;
    },
  },
  watch: {
    selectionLookup() {
      // trigger update upon selection change
      if (this.value && this.value.option === 'selection') {
        this.changeValue('selection');
      }
    },
  },
  methods: {
    generateColorer(value) {
      if (!value || value === this.emptyOption) {
        return () => null;
      }
      if (value === 'selection') {
        const isSelected = this.selectionLookup;
        return (column) => (isSelected(column) ? colors.selected : this.notSelectedColor);
      }
      const meta = this.categoricalMetaData.find((d) => d.name === value);
      const lookup = new Map(meta.levels.map(({ name, color }) => [name, color]));
      const toIndex = this.columnToIndex;
      return (column) => lookup.get(meta.data[toIndex(column)]);
    },
    generateLevels(value) {
      if (!value || value === this.emptyOption) {
        return [];
      }
      return this.options.find((d) => d.value === value).options;
    },
    changeValue(value) {
      const wrapper = {
        option: value,
        levels: this.generateLevels(value),
        apply: this.generateColorer(value),
      };
      this.$emit('input', wrapper);
    },
  },
};
</script>

<template lang="pug">
colorer-option(:title="title", :disabled="disabled",
    :options="options", :value="validatedValue", @input="changeValue($event)")
</template>
