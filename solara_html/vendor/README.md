# Vendored libraries

`vue.esm-browser.prod.js` and `vue.esm-browser.js` are `dist/vue.esm-browser.prod.js` and `dist/vue.esm-browser.js` from the npm package `vue@3.5.43`, unchanged.
They are the browser builds that include the template compiler, because component templates are compiled in the browser.
The production build runs in production mode. The other one, which warns about mistakes in a template, runs in development mode (`solara run` without `--production`).
The license is in `LICENSE-vue` (MIT).

To update it:

```bash
npm pack vue@<version>
tar xzf vue-<version>.tgz package/dist/vue.esm-browser.js package/dist/vue.esm-browser.prod.js package/LICENSE
cp package/dist/vue.esm-browser.js package/dist/vue.esm-browser.prod.js solara_html/vendor/
cp package/LICENSE solara_html/vendor/LICENSE-vue
```

Then change the version in this file, and run the unit tests and the browser checks.
