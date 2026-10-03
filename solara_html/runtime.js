// Shared browser runtime for solara-html components (an ipyreact ES module).
//
// Every component file becomes a Vue 3 app that lives in a shadow root. This module
// - connects the Python traits (ipyreact props) to Vue state, and Vue state back to Python,
// - turns each Python event into a method of the Vue component,
// - loads the component's script (and the files it imports) itself, so that an error in them stays in the component,
// - guards the DOM against unsafe attributes and provides the safe `v-safe-html` directive.
import * as React from "react";
import { createApp, reactive, toRaw, watch } from "solara-html-vue";

// Returns the React component for one HTML component file.
// ipyreact passes each trait as a prop, a set<Name> setter per trait,
// each Python event as a callable prop, and the widget children.
export function defineHtmlComponent({ template, css, modules, entry, propNames, eventNames }) {
  return function HtmlComponent(props) {
    const hostRef = React.useRef(null);
    const propsRef = React.useRef(props);
    const appRef = React.useRef(null);
    propsRef.current = props;

    React.useLayoutEffect(() => {
      const root = hostRef.current.shadowRoot || hostRef.current.attachShadow({ mode: "open" });
      if (css) {
        const sheet = new CSSStyleSheet();
        sheet.replaceSync(css);
        root.adoptedStyleSheets = [sheet];
      }
      // `display: contents` keeps this wrapper out of the layout.
      const container = document.createElement("div");
      container.style.display = "contents";
      // Errors from the template or the script show here, because a console message is easy to miss.
      const errorBox = document.createElement("pre");
      errorBox.style.cssText = "color: #b00020; white-space: pre-wrap; font: 12px monospace; margin: 0;";
      errorBox.hidden = true;
      root.replaceChildren(errorBox, container);
      const report = (message) => {
        errorBox.textContent = message;
        errorBox.hidden = false;
      };

      let app = null;
      let cancelled = false;
      const start = (component) => {
        try {
          app = mountApp({ container, template, component, propNames, eventNames, propsRef, report });
        } catch (error) {
          // A template error must not break the rest of the page. Show it where the component should be.
          console.error("solara-html: cannot mount the component", error);
          report(`solara-html: cannot mount the component\n${error?.message ?? error}`);
        }
        appRef.current = app;
      };
      if (entry === null) {
        start(null);
      } else {
        loadScript(modules, entry).then(
          (component) => {
            if (!cancelled) start(component);
          },
          (error) => {
            console.error("solara-html: cannot load the script", error);
            if (!cancelled) report(`solara-html: cannot load the script\n${error?.message ?? error}`);
          },
        );
      }
      const stopGuard = guardDom(root);
      return () => {
        cancelled = true;
        stopGuard();
        app?.dispose();
        appRef.current = null;
      };
    }, []);

    // After every render: hand the props that Python changed to Vue.
    React.useEffect(() => appRef.current?.update(propsRef.current));

    // Children stay in the light DOM; the browser shows them at the template's <slot>.
    return React.createElement("div", { ref: hostRef }, props.children);
  };
}

// --- The component's script ----------------------------------------------------------------------------------------

// Python sends the script, and the files it imports, as text. Each becomes a blob module, loaded with `importShim`
// (the loader of ipyreact), so that bare imports such as "react" resolve as they do for any ipyreact module.
// A module is loaded once per page. The result, a failure too, is kept by the id, which comes from the content.
const loadedModules = new Map();
const moduleFiles = new Map(); // blob URL -> file name, to name the file in error messages


function loadModule(id, byId) {
  if (!loadedModules.has(id)) {
    loadedModules.set(
      id,
      (async () => {
        const module = byId.get(id);
        const dependencies = await Promise.all(module.imports.map((dependency) => loadModule(dependency, byId)));
        let code = module.code;
        module.imports.forEach((dependency, index) => (code = code.split(dependency).join(dependencies[index].url)));
        const url = URL.createObjectURL(new Blob([code], { type: "text/javascript" }));
        moduleFiles.set(url, module.file);
        try {
          return { url, namespace: await (globalThis.importShim ? globalThis.importShim(url) : import(/* webpackIgnore: true */ url)) };
        } catch (error) {
          throw new Error(`${module.file}: ${describe(error, module.imports.map((dependency) => byId.get(dependency).file))}`);
        }
      })(),
    );
  }
  return loadedModules.get(id);
}

// The browser names a module by its blob URL. Say the file name instead. When ipyreact's loader rewrote the module,
// the URL in the message is one of its own, and the file is one of the imported files.
function describe(error, importedFiles) {
  let text = `${error?.name && error.name !== "Error" ? error.name + ": " : ""}${error?.message ?? error}`;
  for (const [url, file] of moduleFiles) text = text.split(url).join(file);
  if (importedFiles.length) text = text.replace(/'blob:[^']*'/g, `'${importedFiles.join("' or '")}'`);
  return text;
}

async function loadScript(modules, entry) {
  const byId = new Map(modules.map((module) => [module.id, module]));
  const { namespace } = await loadModule(entry, byId);
  if (namespace.component === undefined) warn(`${byId.get(entry).file} does not export "component"`);
  return namespace.component !== null && typeof namespace.component === "object" ? namespace.component : null;
}

// A copy that the app can change without changing the object that ipyreact holds for the widget.
function clone(value) {
  if (value === null || typeof value !== "object") return value;
  try {
    return structuredClone(toRaw(value));
  } catch {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return value; // not copyable (for example a circular object): use it as it is
    }
  }
}

function same(a, b) {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object") return false;
  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return false;
  }
}

function mountApp({ container, template, component, propNames, eventNames, propsRef, report }) {
  const props = propsRef.current;
  const state = reactive({});
  // `lastSent` is the value that Python and the browser last agreed on. A change to `state` that differs from it,
  // such as `this.items.push(x)`, is sent to Python too.
  const lastSent = {};
  for (const name of propNames) {
    state[name] = clone(props[name]);
    lastSent[name] = clone(props[name]);
  }
  // Python props show up at once when the browser writes them, and are then sent to Python.
  // A later render only replaces the local value when Python really changed the prop since
  // the last render, so a late echo of an old value cannot undo a newer write.
  const lastSeen = { ...props };

  const send = (name) => {
    lastSent[name] = clone(state[name]);
    const setter = propsRef.current[setterName(name)];
    if (typeof setter === "function") setter(clone(state[name]));
    else warn(`cannot set "${name}": no setter`);
  };

  const options = component || {};
  const computed = { ...(options.computed || {}) };
  const methods = { ...(options.methods || {}) };

  for (const name of propNames) {
    if (name in computed || name in methods) throw new Error(`solara-html: "${name}" is a Python prop, so a computed property or a method cannot have this name`);
    computed[name] = {
      get: () => state[name],
      set: (value) => {
        state[name] = clone(value);
        send(name);
      },
    };
  }
  for (const name of eventNames) {
    if (name in computed || name in methods) throw new Error(`solara-html: "${name}" is a Python event, so a computed property or a method cannot have this name`);
    methods[name] = (data) => {
      const callback = propsRef.current[name];
      if (typeof callback !== "function") return warn(`event "${name}" has no Python callback`);
      // A bare `@click="reset"` passes the DOM event. Python cannot receive that, so send nothing.
      // ipyreact drops an undefined argument, and the Python callback would then get no argument at all.
      callback(data === undefined || data instanceof Event ? null : data);
    };
  }

  const app = createApp({
    ...options,
    template,
    inheritAttrs: false,
    computed,
    methods,
  });
  app.config.warnHandler = (message) => warn(message);
  app.config.errorHandler = (error, _instance, info) => {
    // In the production build of Vue, `info` is a link to its error reference, not a name.
    console.error("solara-html: error in the template or script", error);
    report(`solara-html: error in the template or script\n${error?.message ?? error}\n(${info})`);
  };
  app.directive("safe-html", {
    mounted: (element, binding) => element.replaceChildren(...sanitizeHtml(binding.value)),
    updated: (element, binding) => {
      if (binding.value !== binding.oldValue) element.replaceChildren(...sanitizeHtml(binding.value));
    },
  });
  app.mount(container);

  // Watched after the mount, so that an assignment made while mounting is not sent twice.
  // The callback runs once per tick, however many changes a method makes.
  const stops = propNames.map((name) =>
    watch(
      () => state[name],
      () => {
        if (!same(state[name], lastSent[name])) send(name);
      },
      { deep: true },
    ),
  );

  return {
    update(next) {
      for (const name of propNames) {
        if (next[name] !== lastSeen[name]) {
          lastSeen[name] = next[name];
          if (!same(state[name], next[name])) state[name] = clone(next[name]);
          lastSent[name] = clone(next[name]);
        }
      }
    },
    dispose: () => {
      stops.forEach((stop) => stop());
      app.unmount();
    },
  };
}

function setterName(name) {
  return `set${name.charAt(0).toUpperCase()}${name.slice(1)}`;
}

function warn(message) {
  console.warn(`solara-html: ${message}`);
}

// --- Safety -------------------------------------------------------------------------------------------------------

const URL_ATTRIBUTES = new Set(["href", "src", "action", "formaction", "poster", "data", "xlink:href"]);
const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);

// A relative URL resolves against the page, so it gets the page's protocol.
function isSafeUrl(value) {
  try {
    return SAFE_PROTOCOLS.has(new URL(value, document.baseURI).protocol);
  } catch {
    return false;
  }
}

// Removes the attributes that can run code, whichever way a binding set them (`:href`, `v-bind="object"`,
// a dynamic attribute name, a DOM property). The browser does not run `javascript:` or an `on*` handler
// before the user acts on it, and this observer runs before that.
function guardDom(root) {
  const check = (element) => {
    for (const { name, value } of [...element.attributes]) {
      const lower = name.toLowerCase();
      if (lower.startsWith("on") || lower === "srcdoc") {
        warn(`removed the attribute "${name}"`);
        element.removeAttribute(name);
      } else if (URL_ATTRIBUTES.has(lower) && !isSafeUrl(value)) {
        warn(`removed the unsafe URL "${value}" from the attribute "${name}"`);
        element.removeAttribute(name);
      }
    }
  };
  const checkTree = (node) => {
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    check(node);
    node.querySelectorAll("*").forEach(check);
  };
  const observer = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "attributes") check(record.target);
      else record.addedNodes.forEach(checkTree);
    }
  });
  root.childNodes.forEach(checkTree);
  observer.observe(root, { subtree: true, childList: true, attributes: true });
  return () => observer.disconnect();
}

const ALLOWED_TAGS = new Set(
  "a abbr b blockquote br caption code del div em h1 h2 h3 h4 h5 h6 hr i img ins kbd li mark ol p pre s small span strong sub sup table tbody td tfoot th thead tr u ul".split(" "),
);
const DROPPED_TAGS = new Set(["script", "style", "iframe", "frame", "object", "embed", "template", "noscript", "svg", "math", "form", "input", "button", "textarea", "select", "link", "meta", "base"]);
const ALLOWED_ATTRIBUTES = { "*": ["title", "lang", "dir", "class"], a: ["href"], img: ["src", "alt", "width", "height"], td: ["colspan", "rowspan"], th: ["colspan", "rowspan"] };

// For `v-safe-html`: parses the text in an inert document, and keeps only known tags and attributes.
function sanitizeHtml(html) {
  const parsed = new DOMParser().parseFromString(`<body>${html ?? ""}</body>`, "text/html");
  const clean = (parent) => {
    for (const child of [...parent.childNodes]) {
      if (child.nodeType === Node.COMMENT_NODE) {
        child.remove();
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        const tag = child.localName;
        if (DROPPED_TAGS.has(tag)) {
          child.remove();
          continue;
        }
        clean(child);
        if (!ALLOWED_TAGS.has(tag)) {
          child.replaceWith(...child.childNodes);
          continue;
        }
        const allowed = [...ALLOWED_ATTRIBUTES["*"], ...(ALLOWED_ATTRIBUTES[tag] || [])];
        for (const { name, value } of [...child.attributes]) {
          const keep = allowed.includes(name) || name.startsWith("data-") || name.startsWith("aria-");
          if (!keep || (URL_ATTRIBUTES.has(name) && !isSafeUrl(value))) child.removeAttribute(name);
        }
        if (tag === "a") child.setAttribute("rel", "noopener noreferrer");
      }
    }
  };
  clean(parsed.body);
  return [...parsed.body.childNodes];
}
