// The source of tex2svg.js: MathJax 4 as one function for the bot's Python,
// tex2svg(latex, display, widthEm) -> an SVG string (task 99). The bundle
// runs in V8 inside the process (services/mathjax.py, through mini-racer),
// where there is no require() and nothing to load a file with, so everything
// MathJax needs is in it, and nothing is fetched while a document is drawn.
//
// Built once, on a developer's machine, and vendored — no Node at build or
// run time on Railway. In a scratch directory:
//
//   npm install @mathjax/src@4.1.3 @mathjax/mathjax-newcm-font@4.1.3
//   cp <repo>/app/assets/mathjax/entry.js .
//   npx esbuild@0.25.12 entry.js --bundle --format=iife --platform=neutral \
//     --main-fields=main,module --minify --define:PACKAGE_VERSION="'4.1.3'" \
//     --outfile=<repo>/app/assets/mathjax/tex2svg.js
//
// PACKAGE_VERSION is defined because MathJax otherwise reads its version out
// of its package.json with an eval'd require(), which V8 alone does not have.
// MathJax and its font are both Apache-2.0: LICENSE beside this file.

const {mathjax} = require('@mathjax/src/cjs/mathjax.js');
const {TeX} = require('@mathjax/src/cjs/input/tex.js');
const {SVG} = require('@mathjax/src/cjs/output/svg.js');
const {liteAdaptor} = require('@mathjax/src/cjs/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('@mathjax/src/cjs/handlers/html.js');
const {MathJaxNewcmFont} = require('@mathjax/mathjax-newcm-font/cjs/svg.js');

// The TeX packages: LaTeX and AMS as a lecture writes them. Left out are the
// ones that change what a standard command draws — physics makes \div a
// divergence, bboldx draws \mathbb from a font of its own, which is not
// here, so ℝ came out an upright R — the ones that want a font or a file
// this bundle does not carry (bbm, dsfont, bussproofs, require, autoload),
// and the ones that would hide an error: noerrors and noundefined print a
// formula they cannot read as its source in red, where the document wants
// to know, and to ask mathtext instead.
const PACKAGES = {
  base: require('@mathjax/src/cjs/input/tex/base/BaseConfiguration.js'),
  ams: require('@mathjax/src/cjs/input/tex/ams/AmsConfiguration.js'),
  amscd: require('@mathjax/src/cjs/input/tex/amscd/AmsCdConfiguration.js'),
  bbox: require('@mathjax/src/cjs/input/tex/bbox/BboxConfiguration.js'),
  boldsymbol: require('@mathjax/src/cjs/input/tex/boldsymbol/BoldsymbolConfiguration.js'),
  braket: require('@mathjax/src/cjs/input/tex/braket/BraketConfiguration.js'),
  cancel: require('@mathjax/src/cjs/input/tex/cancel/CancelConfiguration.js'),
  cases: require('@mathjax/src/cjs/input/tex/cases/CasesConfiguration.js'),
  centernot: require('@mathjax/src/cjs/input/tex/centernot/CenternotConfiguration.js'),
  color: require('@mathjax/src/cjs/input/tex/color/ColorConfiguration.js'),
  configmacros: require('@mathjax/src/cjs/input/tex/configmacros/ConfigMacrosConfiguration.js'),
  empheq: require('@mathjax/src/cjs/input/tex/empheq/EmpheqConfiguration.js'),
  enclose: require('@mathjax/src/cjs/input/tex/enclose/EncloseConfiguration.js'),
  extpfeil: require('@mathjax/src/cjs/input/tex/extpfeil/ExtpfeilConfiguration.js'),
  gensymb: require('@mathjax/src/cjs/input/tex/gensymb/GensymbConfiguration.js'),
  mathtools: require('@mathjax/src/cjs/input/tex/mathtools/MathtoolsConfiguration.js'),
  mhchem: require('@mathjax/src/cjs/input/tex/mhchem/MhchemConfiguration.js'),
  newcommand: require('@mathjax/src/cjs/input/tex/newcommand/NewcommandConfiguration.js'),
  textcomp: require('@mathjax/src/cjs/input/tex/textcomp/TextcompConfiguration.js'),
  textmacros: require('@mathjax/src/cjs/input/tex/textmacros/TextMacrosConfiguration.js'),
  unicode: require('@mathjax/src/cjs/input/tex/unicode/UnicodeConfiguration.js'),
  units: require('@mathjax/src/cjs/input/tex/units/UnitsConfiguration.js'),
  upgreek: require('@mathjax/src/cjs/input/tex/upgreek/UpgreekConfiguration.js'),
  verb: require('@mathjax/src/cjs/input/tex/verb/VerbConfiguration.js'),
};

// The font's glyphs beyond its core come in ranges MathJax loads when a
// formula first needs one. Over every record in the database only four were
// needed — Cyrillic, calligraphic, the mathematical and the other symbols —
// and the bundle carries those and the ones beside them a lecture may reach
// for: about 3.7 MB, where all forty made 11.8 MB and twice the memory. A
// character none of them has is drawn by MathJax as <text>, which the
// process gives no font, and services/mathjax.py refuses such a formula.
const RANGES = {
  'cyrillic': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/cyrillic.js'),
  'math': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/math.js'),
  'symbols': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/symbols.js'),
  'calligraphic': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/calligraphic.js'),
  'arrows': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/arrows.js'),
  'marrows': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/marrows.js'),
  'shapes': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/shapes.js'),
  'mshapes': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/mshapes.js'),
  'double-struck': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/double-struck.js'),
  'fraktur': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/fraktur.js'),
  'script': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/script.js'),
  'accents': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/accents.js'),
  'variants': () => require('@mathjax/mathjax-newcm-font/cjs/svg/dynamic/variants.js'),
};

// A range is loaded the moment a formula needs it, synchronously: the
// module is already in the bundle, and MathJax, told its loader is
// synchronous, never asks to be called again once it has loaded.
mathjax.asyncIsSynchronous = true;
mathjax.asyncLoad = (name) => {
  const range = RANGES[name.replace(/^.*\//, '').replace(/\.js$/, '')];
  if (!range) throw new Error('no font range ' + name);
  return range();
};

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({
  packages: Object.keys(PACKAGES),
  // A circled sign — record 50's ① and ⓪ — as the enclose package draws a
  // circle round its argument; MathJax has no \textcircled of its own.
  macros: {textcircled: ['\\enclose{circle}{\\kern1mu #1\\kern1mu}', 1]},
  // A formula MathJax cannot read throws, rather than drawing its error.
  formatError: (jax, error) => { throw error; },
});
const svg = new SVG({
  fontData: MathJaxNewcmFont,
  // Every glyph a path of its own, nothing shared through <use>, so the SVG
  // stands alone for the rasteriser.
  fontCache: 'none',
  // A display formula wider than the width it is given is broken, at a
  // relation or an operation, into lines that fit it — record 102's
  // expansion of a 5 × 5 determinant was shrunk to a fraction of the text.
  displayOverflow: 'linebreak',
  // A formula in a line is one picture in the paragraph: broken, it came
  // back as one <svg> a piece, and the document took only the first.
  linebreaks: {inline: false},
});
const html = mathjax.document('', {InputJax: tex, OutputJax: svg});

globalThis.tex2svg = function (latex, display, widthEm) {
  let node;
  try {
    node = html.convert(latex, {display: !!display, em: 16, ex: 8, containerWidth: widthEm * 16});
  } catch (error) {
    // TeX's errors are objects with a message, not Errors: through V8 they
    // arrived as "[object Object]".
    throw new Error(error && error.message ? error.message : String(error));
  }
  return adaptor.outerHTML(adaptor.firstChild(node));
};
