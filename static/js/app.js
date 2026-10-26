/* Janjé storefront interactions (jQuery) */
$(function () {
  "use strict";

  var U = window.JANJE.urls;
  $.ajaxSetup({ headers: { "X-CSRFToken": $('meta[name="csrf-token"]').attr("content") } });

  function rupees(n) {
    return "₹" + Math.round(n).toLocaleString("en-IN");
  }

  /* ---------------------------------------------------------------- toasts */
  function toast(message, isError) {
    if (!message) return;
    var $t = $('<div class="js-toast pointer-events-auto w-full px-5 py-3 rounded-full shadow-lg text-sm font-bold flex items-center gap-2" role="status"></div>')
      .addClass(isError ? "bg-error-container text-on-error-container" : "bg-cocoa text-white")
      .text(message);
    $("#toast-stack").append($t);
    dismissLater($t);
  }

  function dismissLater($t) {
    setTimeout(function () {
      $t.fadeOut(300, function () { $t.remove(); });
    }, 3800);
  }

  $(".js-toast").each(function () { dismissLater($(this)); });

  function errorText(xhr, fallback) {
    return (xhr.responseJSON && xhr.responseJSON.error) || fallback || "Something went wrong. Please try again.";
  }

  /* ----------------------------------------------------------- mobile menu */
  $(document).on("click", ".js-menu", function () {
    var open = $(this).attr("aria-expanded") !== "true";
    $(this).attr({ "aria-expanded": open, "aria-label": open ? "Close menu" : "Open menu" });
    $(this).find(".js-menu-open").toggleClass("hidden", open);
    $(this).find(".js-menu-close").toggleClass("hidden", !open);
    $("#mobile-nav").toggleClass("hidden", !open).toggleClass("flex", open);
  });
  $(document).on("click", "#mobile-nav a", function () {
    $(".js-menu[aria-expanded=true]").trigger("click");
  });

  /* ------------------------------------------------------------------ cart */
  var $cart = $("#cart-body");

  function setBagCount(n) {
    $("#bag-count").text(n);
    $('a[href="' + U.cart + '"][aria-label^="Cart"]').attr("aria-label", "Cart, " + n + " items");
  }

  function renderBag(res) {
    setBagCount(res.count);
    if ($cart.length) $cart.html(res.html);
  }

  $(document).on("click", ".js-bag-qty", function () {
    $.post(U.bagUpdate, { key: $(this).data("key"), qty: $(this).data("qty") }).done(renderBag);
  });

  $(document).on("click", ".js-add-addon", function () {
    $.post(U.bagAddOn, { addon_id: $(this).data("addon-id") }).done(function (res) {
      renderBag(res);
      toast(res.message);
    });
  });

  $(document).on("click", ".js-note-edit", function () {
    $(".js-note-view").addClass("hidden");
    $(".js-note-form").removeClass("hidden").addClass("flex").find("textarea").trigger("focus");
  });
  $(document).on("click", ".js-note-cancel", function () {
    $(".js-note-form").addClass("hidden").removeClass("flex");
    $(".js-note-view").removeClass("hidden");
  });
  $(document).on("submit", ".js-note-form", function (e) {
    e.preventDefault();
    $.post(U.bagNote, { note: $(this).find("textarea").val() }).done(function (res) {
      renderBag(res);
      toast(res.message);
    });
  });

  function addToBag(data) {
    return $.post(U.bagAdd, data).fail(function (xhr) { toast(errorText(xhr), true); });
  }

  // Product cards: add in place, the button turns into "Added"
  $(document).on("click", ".js-quick-add", function () {
    var $btn = $(this).prop("disabled", true);
    addToBag({ product_id: $btn.data("product-id"), qty: 1 })
      .done(function (res) {
        renderBag(res);
        $btn.text("Added").removeClass("btn-berry").addClass("bg-blush text-cocoa");
        toast(res.message);
      })
      .always(function () { $btn.prop("disabled", false); });
  });

  $(document).on("click", ".js-reorder", function () {
    var ids = String($(this).data("products")).split(",").filter(Boolean);
    var chain = $.Deferred().resolve().promise();
    ids.forEach(function (id) {
      chain = chain.then(function () { return addToBag({ product_id: id, qty: 1 }); });
    });
    chain.done(function () { window.location.href = U.cart; });
  });

  /* -------------------------------------------------------------- wishlist */
  $(document).on("click", ".js-wishlist", function (e) {
    e.preventDefault();
    var $btn = $(this);
    $.post(U.wishlistToggle, { product_id: $btn.data("product-id") }).done(function (res) {
      var $all = $('.js-wishlist[data-product-id="' + $btn.data("product-id") + '"]');
      $all.toggleClass("is-wished", res.added).find(".heart").text(res.added ? "♥" : "♡");
      toast(res.added ? "Saved to your wishlist ♡" : "Removed from your wishlist");
    });
  });
  $(".js-wishlist.is-wished .heart").text("♥");

  /* ------------------------------------------------------------ newsletter */
  $(document).on("submit", ".js-newsletter", function (e) {
    e.preventDefault();
    var $form = $(this);
    $.post(U.newsletter, $form.serialize())
      .done(function (res) { toast(res.message); $form[0].reset(); })
      .fail(function (xhr) { toast(errorText(xhr), true); });
  });

  /* ------------------------------------------------------ misc page helpers */
  $(document).on("change", ".js-autosubmit", function () { $(this).closest("form").trigger("submit"); });

  // Home: category circles and filter pills narrow the product grid
  $(document).on("click", ".js-filter", function () {
    var filter = $(this).data("filter");
    $(".js-filter.chip").each(function () {
      var on = $(this).data("filter") === filter;
      $(this).toggleClass("is-on", on).attr("aria-selected", on);
    });
    $(".js-filter .js-cat-ring").each(function () {
      var on = $(this).closest(".js-filter").data("filter") === filter;
      $(this).css("box-shadow", "0 0 0 2px " + (on ? "#B4485F" : "#EBC3CA"));
    });
    var shown = 0;
    $("#bestseller-grid .js-product-card").each(function () {
      var match = filter === "all" || $(this).data("category") === filter;
      $(this).toggle(match);
      if (match) shown++;
    });
    $("#bestseller-grid .js-filter-empty").toggleClass("hidden", shown > 0);
  });

  // Account page
  $(document).on("click", ".js-toggle-address", function () {
    $(".js-address-form").toggleClass("hidden");
  });
  $(document).on("click", ".js-use-note", function () {
    $.post(U.bagNote, { note: $(this).data("note") }).done(function (res) {
      setBagCount(res.count);
      toast("Note saved. It'll be on your next gift ♡");
    });
  });
  $(document).on("click", ".js-copy", function () {
    var text = $(this).siblings(".js-copy-source").val();
    if (navigator.clipboard) navigator.clipboard.writeText(text);
    toast("Copied " + text + " ♡");
  });

  /* ------------------------------------------------------- product details */
  var $pdp = $("#pdp-form");
  if ($pdp.length) {
    var pdp = JSON.parse(document.getElementById("pdp-data").textContent);
    var base = pdp.basePrice, compare = pdp.baseCompare, qty = 1;

    var updatePrice = function () {
      var pct = compare > base ? Math.round((1 - base / compare) * 100) : 0;
      $("#price-display").text(rupees(base));
      $("#regular-price-display").text(rupees(compare)).toggleClass("hidden", !pct);
      $("#save-badge").text("Save " + pct + "%").toggleClass("hidden", !pct);
      $("#mbar-price").text(rupees(base * qty));
      $("#mbar-qty").text(qty);
      $("#qty-input").val(qty);
    };

    var pick = function ($group, $on) {
      $group.removeClass("is-on").attr("aria-pressed", "false");
      $on.addClass("is-on").attr("aria-pressed", "true");
    };

    $pdp.on("click", ".js-size", function () {
      pick($pdp.find(".js-size"), $(this));
      base = parseFloat($(this).data("price"));
      compare = parseFloat($(this).data("compare"));
      $("#size-input").val($(this).data("size-id"));
      $("#selected-size-name").text($(this).data("name"));
      updatePrice();
    });

    $pdp.on("click", ".js-color", function () {
      pick($pdp.find(".js-color"), $(this));
      $("#selected-color-name").text($(this).data("label"));
      $("#color-input").val($(this).data("color-id"));
    });

    $pdp.on("click", ".js-qty", function () {
      qty = Math.max(1, Math.min(20, qty + parseInt($(this).data("delta"), 10)));
      $("#qty-val").text(qty);
      updatePrice();
    });

    $pdp.on("submit", function (e) {
      e.preventDefault();
      var $btns = $(".js-add-to-bag").prop("disabled", true).text("Adding…");
      addToBag($pdp.serialize())
        .done(function (res) { window.location.href = res.redirect; })
        .fail(function () { $btns.prop("disabled", false).text("Add to cart"); });
    });
  }

  $(document).on("click", ".js-thumb", function () {
    $("#main-product-img").attr("src", $(this).data("src"));
    $(".js-thumb").removeClass("border-berry").addClass("border-white").attr("aria-pressed", "false");
    $(this).removeClass("border-white").addClass("border-berry").attr("aria-pressed", "true");
  });

  $(document).on("click", ".js-write-review", function () {
    $(".js-review-form").toggleClass("hidden").find("textarea").trigger("focus");
  });

  /* -------------------------------------------------------------- checkout */
  var $checkout = $("#checkout-form");

  function currentPayment() {
    return $checkout.find('input[name="payment_method"]:checked').val() || "upi";
  }

  function refreshSummary() {
    $.get(U.checkoutSummary, { payment: currentPayment() }).done(function (html) {
      $("#checkout-summary").html(html);
      $("#mbar-total").text($("#summary-total").data("total"));
    });
  }

  if ($checkout.length) {
    var ncr = String($checkout.data("ncr")).split(",");
    var $status = $("#pincode-status"), defaultStatus = $status.text();

    $("#id_pincode").on("input", function () {
      var pin = $.trim($(this).val());
      if (!/^[1-9]\d{5}$/.test(pin)) {
        $status.text(defaultStatus);
        return;
      }
      var isNcr = ncr.some(function (p) { return pin.indexOf(p) === 0; });
      $status.text(isNcr ? "Yay, you’re in Delhi NCR: hand delivery in 24–48 hours" : "We’ll courier it to you in 3–5 working days");
    }).trigger("input");

    $checkout.on("change", 'input[name="payment_method"]', function () {
      $checkout.find(".js-pay").each(function () {
        var on = $(this).find("input").is(":checked");
        $(this).toggleClass("border-berry bg-cream", on).toggleClass("border-blush-line bg-white", !on);
      });
      refreshSummary();
    });

    function applyCoupon(code) {
      $.post(U.bagCoupon, { code: code })
        .done(function (res) { toast(res.message); refreshSummary(); })
        .fail(function (xhr) { toast(errorText(xhr), true); refreshSummary(); });
    }
    $checkout.on("click", ".js-coupon-apply", function () {
      applyCoupon($checkout.find(".js-coupon-input").val());
    });
    $checkout.on("click", ".js-coupon-remove", function () { applyCoupon(""); });
    $checkout.on("keydown", ".js-coupon-input", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        applyCoupon($(this).val());
      }
    });

    $checkout.on("submit", function () {
      $checkout.find(".js-place-order").prop("disabled", true).text("Placing order…");
    });
  }
});
