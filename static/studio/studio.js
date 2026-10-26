/* Janjé Studio dashboard interactions */
$(function () {
  "use strict";

  $.ajaxSetup({ headers: { "X-CSRFToken": $('meta[name="csrf-token"]').attr("content") } });

  function flash(message, isError) {
    var $m = $('<div class="st-msg" role="status"></div>').toggleClass("is-err", !!isError).text(message);
    var $box = $(".st-messages");
    if (!$box.length) $box = $('<div class="st-messages"></div>').insertAfter(".st-top");
    $box.append($m);
    setTimeout(function () { $m.fadeOut(300, function () { $m.remove(); }); }, 2500);
  }

  /* ------------------------------------------------- list: switches & order */
  $(document).on("click", ".js-toggle", function () {
    var $b = $(this);
    $.post($b.data("url"), { field: $b.data("field") })
      .done(function (res) { $b.attr("aria-pressed", res.value ? "true" : "false"); flash("Saved"); })
      .fail(function () { flash("Couldn't save that. Try again.", true); });
  });

  $(".js-sortable").each(function () {
    var el = this;
    Sortable.create(el, {
      handle: ".js-grip", animation: 150,
      onEnd: function () {
        var ids = $(el).children("tr").map(function () { return $(this).data("id"); }).get();
        $.ajax({ url: $(el).data("url"), method: "POST", contentType: "application/json", data: JSON.stringify({ ids: ids }) })
          .done(function () { flash("New order saved"); });
      }
    });
  });

  /* ------------------------------------------- product sizes, colours, photos */
  function renumber($formset) {
    $formset.find(".js-rows > .js-row").each(function (i) {
      $(this).find('input[name$="-sort_order"]').val(i);
    });
  }

  $(".js-formset").each(function () {
    var $fs = $(this);
    var rows = $fs.find(".js-rows")[0];
    Sortable.create(rows, { handle: ".js-row-grip", animation: 150, onEnd: function () { renumber($fs); } });
  });

  $(document).on("click", ".js-add-row", function () {
    var $fs = $(this).closest(".js-formset");
    var prefix = $fs.data("prefix");
    var $total = $fs.find('input[name="' + prefix + '-TOTAL_FORMS"]');
    var index = parseInt($total.val(), 10);
    var html = $fs.find("template.js-empty").html().replace(/__prefix__/g, index);
    var $row = $(html);
    $fs.find(".js-rows").append($row);
    $total.val(index + 1);
    renumber($fs);
    $row.find("input:not([type=hidden]), select").first().trigger("focus");
  });

  $(document).on("click", ".js-remove-row", function () {
    var $row = $(this).closest(".js-row");
    $row.find('input[name$="-DELETE"]').prop("checked", true);
    $row.addClass("is-removed");
  });

  /* ------------------------------------------------------- home page layout */
  $(".js-sections").each(function () {
    var $list = $(this);
    function save() {
      var order = [], visible = {};
      $list.children("li").each(function () {
        var key = $(this).data("key");
        order.push(key);
        visible[key] = $(this).find(".js-section-visible").is(":checked");
      });
      $.ajax({ url: $list.data("url"), method: "POST", contentType: "application/json",
        data: JSON.stringify({ page: $list.data("page"), order: order, visible: visible }) })
        .done(function () { flash("Layout saved"); });
    }
    Sortable.create(this, { handle: ".js-grip", animation: 150, onEnd: save });
    $list.on("change", ".js-section-visible", save);
  });

  /* ----------------------------------------------------------- text screen */
  function syncColor($form) {
    var on = $form.find(".js-color-on").is(":checked");
    $form.find('input[name="color"]').val(on ? $form.find(".js-color-val").val().toUpperCase() : "");
  }
  $(document).on("change input", ".js-color-on, .js-color-val", function () {
    if ($(this).hasClass("js-color-val")) $(this).siblings(".js-color-on").prop("checked", true);
    syncColor($(this).closest("form"));
  });

  /* ---------------------------------------------------- appearance preview */
  var $preview = $("#theme-preview");
  if ($preview.length) {
    var $form = $("#appearance-form");
    var map = {
      color_primary: "--p", color_text: "--pv-text", color_muted: "--pv-muted", color_background: "--pv-bg",
      color_soft: "--pv-soft", color_line: "--pv-line", color_yellow: "--pv-yellow", color_lilac: "--pv-lilac", color_blue: "--pv-blue"
    };
    var paint = function () {
      var el = $preview[0];
      $.each(map, function (field, cssVar) {
        var $input = $form.find('[name="' + field + '"]');
        el.style.setProperty(cssVar, $input.val());
        $input.closest("label").find(".js-hex").text($input.val().toUpperCase());
      });
      el.style.setProperty("--pv-heading", "'" + $form.find('[name="font_heading"]').val() + "', cursive");
      el.style.setProperty("--pv-body", "'" + $form.find('[name="font_body"]').val() + "', sans-serif");
      el.style.setProperty("--pv-logo", "'" + $form.find('[name="font_logo"]').val() + "', cursive");
      el.style.setProperty("--pv-size", ($form.find('[name="base_font_size"]').val() || 16) + "px");
      $preview.find(".pv-bar").toggle($form.find('[name="show_announcement"]').is(":checked"));
    };
    $form.on("input change", paint);
    paint();
  }
});
