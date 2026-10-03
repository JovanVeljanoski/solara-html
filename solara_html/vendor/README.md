# Vendored libraries

`vue.esm-browser.prod.js` is `dist/vue.esm-browser.prod.js` from the npm package `vue@3.5.43`, unchanged.
It is the browser build that includes the template compiler, because component templates are compiled in the browser.
Its license is in `LICENSE-vue` (MIT).

To update it:

```bash
npm pack vue@<version>
tar xzf vue-<version>.tgz package/dist/vue.esm-browser.prod.js package/LICENSE
cp package/dist/vue.esm-browser.prod.js solara_html/vendor/
cp package/LICENSE solara_html/vendor/LICENSE-vue
```

Then change the version in this file, and run the unit tests and the browser checks.
