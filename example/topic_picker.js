// A child component for quiz.html: a plain ES module that exports a Vue options object with a template string.
// quiz.html imports it with a relative import, and registers it in its `components`.
// Its styles live in quiz.html: a component file has one stylesheet, and the child shares the shadow root.
export default {
  props: {
    modelValue: { type: Array, default: () => [] },
    topics: { type: Array, default: () => [] },
    done: { type: Array, default: () => [] },
    disabled: Boolean,
  },
  // Between two Vue components, $emit is the normal way to talk to the parent (`v-model` listens to this event).
  emits: ["update:modelValue"],
  data() {
    return { search: "", open: false };
  },
  computed: {
    filtered() {
      const query = this.search.toLowerCase();
      return this.topics.filter((topic) => topic.toLowerCase().includes(query));
    },
  },
  methods: {
    isDone(topic) {
      return this.done[this.topics.indexOf(topic)] === 1;
    },
    toggle(topic) {
      const chosen = this.modelValue.includes(topic) ? this.modelValue.filter((t) => t !== topic) : [...this.modelValue, topic];
      this.$emit("update:modelValue", chosen);
      this.search = "";
    },
    // The click comes from inside a shadow root, so check the whole event path.
    closeOnOutsideClick(event) {
      if (!event.composedPath().includes(this.$refs.combo)) this.open = false;
    },
  },
  mounted() {
    document.addEventListener("click", this.closeOnOutsideClick);
  },
  beforeUnmount() {
    document.removeEventListener("click", this.closeOnOutsideClick);
  },
  template: `
    <div ref="combo" class="combo">
      <div class="combo-field" :class="{ disabled }" @click="open = true">
        <span v-for="topic in modelValue" :key="topic" class="chip" :class="{ done: isDone(topic) }">
          {{ topic }}
          <button type="button" class="chip-x" aria-label="Remove topic" @click.stop="toggle(topic)">×</button>
        </span>
        <input v-model="search" type="text" :placeholder="modelValue.length ? '' : 'Choose topics'" :disabled="disabled" @focus="open = true" />
      </div>
      <ul v-if="open" class="combo-list" role="listbox">
        <li
          v-for="topic in filtered"
          :key="topic"
          role="option"
          :aria-selected="modelValue.includes(topic)"
          :class="{ selected: modelValue.includes(topic), done: isDone(topic) }"
          @mousedown.prevent="toggle(topic)"
        >
          <span>{{ topic }}</span>
          <span v-if="isDone(topic)" class="status">✓ Completed</span>
        </li>
        <li v-if="!filtered.length" class="empty">No topics match “{{ search }}”.</li>
      </ul>
    </div>
  `,
};
