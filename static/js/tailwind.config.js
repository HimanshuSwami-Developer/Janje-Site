// Janjé theme. Main colours and fonts come from CSS variables set in base.html
// from Studio › Appearance; the older Stitch token names stay as aliases for the account pages.
(function () {
  var v = function (name) { return "rgb(var(" + name + ") / <alpha-value>)"; };
  var primary = v("--c-primary"), primaryDark = v("--c-primary-dark"), text = v("--c-text"), muted = v("--c-muted"),
    bg = v("--c-bg"), soft = v("--c-soft"), line = v("--c-line"), yellow = v("--c-yellow"), lilac = v("--c-lilac"), blue = v("--c-blue");
  tailwind.config = {theme: {extend: {
    colors: {
      "berry": primary, "berry-dark": primaryDark, "cocoa": text, "cocoa-soft": muted, "cocoa-mid": muted,
      "cream": bg, "blush": soft, "blush-line": line, "butter": yellow, "lilac": lilac, "sky": blue,
      "rose": "#FFF0F3", "blush-deep": "#E3A9B5", "petal": "#F4B6C2", "butter-line": "#D9BE55", "butter-ink": "#6B5320",
      "primary": primary, "on-primary": "#ffffff", "primary-container": "#F4B6C2", "on-primary-container": primaryDark,
      "primary-fixed": soft, "primary-fixed-dim": "#E3A9B5", "on-primary-fixed": text, "on-primary-fixed-variant": primaryDark,
      "inverse-primary": "#F4B6C2", "surface-tint": primary,
      "secondary": muted, "on-secondary": "#ffffff", "secondary-container": lilac, "on-secondary-container": text,
      "secondary-fixed": lilac, "secondary-fixed-dim": "#D6CAEE", "on-secondary-fixed": text, "on-secondary-fixed-variant": muted,
      "tertiary": "#3F6B4E", "on-tertiary": "#ffffff", "tertiary-container": "#CFE5D6", "on-tertiary-container": "#1F3D2A",
      "tertiary-fixed": yellow, "tertiary-fixed-dim": "#F3E08A", "on-tertiary-fixed": text, "on-tertiary-fixed-variant": "#6B5320",
      "error": "#B3261E", "on-error": "#ffffff", "error-container": "#FCE3E0", "on-error-container": "#7A1810",
      "background": bg, "on-background": text, "surface": bg, "surface-bright": bg, "surface-dim": "#F3E3DD",
      "surface-container-lowest": "#ffffff", "surface-container-low": "#FFF0F3", "surface-container": "#FBE6EA",
      "surface-container-high": soft, "surface-container-highest": "#F3D3D9", "surface-variant": "#F3D3D9",
      "on-surface": text, "on-surface-variant": muted, "outline": "#8C6A62", "outline-variant": line,
      "inverse-surface": text, "inverse-on-surface": bg
    },
    borderRadius: {"DEFAULT": "1rem", "lg": "1.5rem", "xl": "1.75rem", "full": "9999px"},
    spacing: {"margin": "1rem", "margin-md": "1.5rem", "margin-lg": "1.5rem", "gutter": "1rem", "gutter-md": "1.5rem", "gutter-lg": "2rem",
      "space-xs": "0.25rem", "space-sm": "0.5rem", "space-md": "1rem", "space-lg": "1.5rem", "space-xl": "2.5rem"},
    fontFamily: {
      "hand": ["var(--font-heading)"], "script": ["var(--font-logo)"], "sans": ["var(--font-body)"],
      "display-lg": ["var(--font-heading)"], "display-lg-mobile": ["var(--font-heading)"], "headline-lg": ["var(--font-heading)"],
      "headline-lg-mobile": ["var(--font-heading)"], "headline-md": ["var(--font-heading)"], "headline-sm": ["var(--font-heading)"],
      "title-lg": ["var(--font-body)"], "title-md": ["var(--font-body)"], "body-lg": ["var(--font-body)"], "body-md": ["var(--font-body)"],
      "body-sm": ["var(--font-body)"], "label-lg": ["var(--font-body)"], "label-md": ["var(--font-body)"], "label-sm": ["var(--font-body)"]
    },
    fontSize: {"display-lg": ["64px", {"lineHeight": "1", "fontWeight": "700"}], "display-lg-mobile": ["48px", {"lineHeight": "1", "fontWeight": "700"}],
      "headline-lg": ["44px", {"lineHeight": "1.05", "fontWeight": "700"}], "headline-lg-mobile": ["36px", {"lineHeight": "1.05", "fontWeight": "700"}],
      "headline-md": ["32px", {"lineHeight": "1.1", "fontWeight": "700"}], "headline-sm": ["26px", {"lineHeight": "1.1", "fontWeight": "700"}],
      "title-lg": ["18px", {"lineHeight": "26px", "fontWeight": "800"}], "title-md": ["16px", {"lineHeight": "24px", "fontWeight": "700"}],
      "body-lg": ["17px", {"lineHeight": "1.6", "fontWeight": "400"}], "body-md": ["15px", {"lineHeight": "1.55", "fontWeight": "400"}], "body-sm": ["13px", {"lineHeight": "1.5", "fontWeight": "400"}],
      "label-lg": ["15px", {"lineHeight": "20px", "fontWeight": "800"}], "label-md": ["13px", {"lineHeight": "18px", "fontWeight": "700"}], "label-sm": ["12px", {"lineHeight": "16px", "fontWeight": "800"}]}
  }}};
})();
