/* Studio on-page editor: click any text to edit it; drag home sections to reorder them. */
$(function () {
  "use strict";

  var S = window.JANJE.studio;
  var blocks = {};
  var current = null; // { key, before: {text, style} }

  $("body").addClass("cms-on");

  function escapeHtml(text) {
    return $("<div>").text(text).html().replace(/\n/g, "<br>");
  }

  function styleFor(b) {
    var rules = [];
    if (b.color) rules.push("color:" + b.color);
    if (b.size) rules.push("font-size:" + b.size + "px");
    if (b.font) rules.push("font-family:var(--font-" + b.font + ")");
    if (b.weight) rules.push("font-weight:" + b.weight);
    if (b.italic) rules.push("font-style:italic");
    return rules.join(";");
  }

  function paint(key, text, style) {
    $('[data-cms="' + key + '"]').html(escapeHtml(text)).attr("style", style || null);
  }

  function notify(message, isError) {
    var $t = $('<div class="js-toast pointer-events-auto w-full px-5 py-3 rounded-full shadow-lg text-sm font-bold" role="status"></div>')
      .addClass(isError ? "bg-error-container text-on-error-container" : "bg-cocoa text-white").text(message);
    $("#toast-stack").append($t);
    setTimeout(function () { $t.fadeOut(300, function () { $t.remove(); }); }, 3000);
  }

  // Load every block on the page so the panel opens instantly
  var keys = [];
  $("[data-cms]").each(function () {
    var k = $(this).data("cms");
    if (keys.indexOf(k) < 0) keys.push(k);
  });
  if (keys.length) {
    $.ajax({ url: S.blocks, data: { key: keys }, traditional: true }).done(function (res) { blocks = res; });
  }

  /* ----------------------------------------------------------------- panel */
  var $panel = $(
    '<aside class="cms-panel" aria-label="Edit text" hidden>' +
      '<div class="cms-panel-head"><strong>Edit text</strong><button type="button" class="cms-x" aria-label="Close">×</button></div>' +
      '<p class="cms-key"></p>' +
      '<label class="cms-row">Text<textarea class="cms-text" rows="4"></textarea></label>' +
      '<div class="cms-grid">' +
        '<label class="cms-row">Colour<span class="cms-color"><input type="checkbox" class="cms-color-on" aria-label="Use a custom colour"><input type="color" class="cms-color-val" value="#B4485F"></span></label>' +
        '<label class="cms-row">Size (px)<input type="number" class="cms-size" min="8" max="200" placeholder="Auto"></label>' +
        '<label class="cms-row">Font<select class="cms-font"><option value="">As designed</option><option value="heading">Headings font</option><option value="body">Body font</option><option value="logo">Logo font</option></select></label>' +
        '<label class="cms-row">Weight<select class="cms-weight"><option value="">As designed</option><option value="400">Regular</option><option value="600">Semibold</option><option value="700">Bold</option><option value="800">Extra bold</option></select></label>' +
      '</div>' +
      '<label class="cms-check"><input type="checkbox" class="cms-italic"> Italic</label>' +
      '<p class="cms-error" role="alert"></p>' +
      '<div class="cms-actions"><button type="button" class="cms-save">Save</button><button type="button" class="cms-cancel">Cancel</button></div>' +
      '<button type="button" class="cms-reset">Reset to the original text &amp; style</button>' +
    "</aside>"
  ).appendTo("body");

  function readPanel() {
    return {
      text: $panel.find(".cms-text").val(),
      color: $panel.find(".cms-color-on").is(":checked") ? $panel.find(".cms-color-val").val().toUpperCase() : "",
      size: $panel.find(".cms-size").val(),
      font: $panel.find(".cms-font").val(),
      weight: $panel.find(".cms-weight").val(),
      italic: $panel.find(".cms-italic").is(":checked")
    };
  }

  function preview() {
    if (!current) return;
    var b = readPanel();
    paint(current.key, b.text, styleFor(b));
  }

  function open(key, el) {
    if (current) close(true);
    var $first = $('[data-cms="' + key + '"]').first();
    var b = blocks[key] || { text: $first.text(), color: "", size: null, font: "", weight: "", italic: false };
    current = { key: key, before: { html: $first.html(), style: $first.attr("style") || "" } };
    $panel.find(".cms-key").text(key);
    $panel.find(".cms-text").val(b.text);
    $panel.find(".cms-color-on").prop("checked", !!b.color);
    $panel.find(".cms-color-val").val(b.color || rgbToHex(getComputedStyle(el).color));
    $panel.find(".cms-size").val(b.size || "");
    $panel.find(".cms-font").val(b.font || "");
    $panel.find(".cms-weight").val(b.weight || "");
    $panel.find(".cms-italic").prop("checked", !!b.italic);
    $panel.find(".cms-error").text("");
    $(".cms-active").removeClass("cms-active");
    $('[data-cms="' + key + '"]').addClass("cms-active");
    $panel.prop("hidden", false);
    $panel.find(".cms-text").trigger("focus");
  }

  function close(revert) {
    if (current && revert) {
      $('[data-cms="' + current.key + '"]').html(current.before.html).attr("style", current.before.style || null);
    }
    $(".cms-active").removeClass("cms-active");
    current = null;
    $panel.prop("hidden", true);
  }

  function rgbToHex(rgb) {
    var m = String(rgb).match(/\d+/g);
    if (!m) return "#4A2C26";
    return "#" + m.slice(0, 3).map(function (n) { return ("0" + parseInt(n, 10).toString(16)).slice(-2); }).join("").toUpperCase();
  }

  function save(extra) {
    var data = $.extend({ key: current.key }, readPanel(), extra || {});
    if (!data.italic) delete data.italic;
    $.ajax({ url: S.save, method: "POST", data: data, headers: { "X-Requested-With": "XMLHttpRequest" } })
      .done(function (res) {
        blocks[current.key] = res.block;
        paint(current.key, res.text, res.style);
        close(false);
        notify(extra && extra.reset ? "Back to the original ♡" : "Saved ♡");
      })
      .fail(function (xhr) {
        $panel.find(".cms-error").text((xhr.responseJSON && xhr.responseJSON.error) || "Couldn't save. Try again.");
      });
  }

  // Clicking text opens the editor instead of following links or buttons
  document.addEventListener("click", function (e) {
    if ($(e.target).closest(".cms-panel, .studio-bar, .cms-section-bar").length) return;
    var el = $(e.target).closest("[data-cms]")[0];
    if (!el) return;
    e.preventDefault();
    e.stopPropagation();
    open($(el).data("cms"), el);
  }, true);

  $panel.on("input change", "textarea, input, select", preview);
  $panel.on("click", ".cms-save", function () { save(); });
  $panel.on("click", ".cms-reset", function () { save({ reset: 1 }); });
  $panel.on("click", ".cms-cancel, .cms-x", function () { close(true); });
  $(document).on("keydown", function (e) {
    if (e.key === "Escape" && current) close(true);
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && current) save();
  });

  /* -------------------------------------------------------------- sections */
  var $sections = $(".cms-section");
  if (!$sections.length) return;
  var page = $sections.first().data("page");
  var $container = $sections.first().parent();

  $sections.each(function () {
    var $s = $(this);
    $s.prepend(
      '<div class="cms-section-bar">' +
        '<span class="cms-grip" aria-hidden="true">⋮⋮</span><strong></strong>' +
        '<button type="button" class="cms-move" data-dir="-1" aria-label="Move up">↑</button>' +
        '<button type="button" class="cms-move" data-dir="1" aria-label="Move down">↓</button>' +
        '<button type="button" class="cms-hide"></button>' +
      "</div>"
    );
    $s.find(".cms-section-bar strong").text($s.data("label"));
    $s.find(".cms-hide").text(String($s.data("visible")) === "1" ? "Hide" : "Show");
  });

  function saveSections() {
    var order = [], visible = {};
    $container.children(".cms-section").each(function () {
      order.push($(this).data("section"));
      visible[$(this).data("section")] = String($(this).data("visible")) === "1";
    });
    $.ajax({
      url: S.sections, method: "POST", contentType: "application/json",
      data: JSON.stringify({ page: page, order: order, visible: visible })
    }).done(function () { notify("Layout saved ♡"); });
  }

  if (window.Sortable) {
    Sortable.create($container[0], { handle: ".cms-section-bar", draggable: ".cms-section", animation: 150, onEnd: saveSections });
  }

  $container.on("click", ".cms-move", function () {
    var $s = $(this).closest(".cms-section");
    if ($(this).data("dir") < 0) $s.prev(".cms-section").before($s); else $s.next(".cms-section").after($s);
    saveSections();
  });

  $container.on("click", ".cms-hide", function () {
    var $s = $(this).closest(".cms-section");
    var nowVisible = String($s.data("visible")) !== "1";
    $s.data("visible", nowVisible ? "1" : "0").toggleClass("is-hidden", !nowVisible);
    $(this).text(nowVisible ? "Hide" : "Show");
    saveSections();
  });
});
