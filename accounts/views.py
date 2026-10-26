from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AddressForm, LoginForm, ProfileForm, SignupForm
from .models import Address, Profile

BLOSSOM_TIERS = [(0, "Tier 1 Bud"), (250, "Tier 2 VIP"), (1000, "Tier 3 Bloom Royalty")]
NEXT_REWARD = 500


def _safe_next(request, default="accounts:account"):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return nxt
    return default


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request, username=form.cleaned_data["email"], password=form.cleaned_data["password"])
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or 'lovely'} ♡")
            return redirect(_safe_next(request))
        form.add_error(None, "That email and password don't match. Please try again.")
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        messages.success(request, "Welcome to the Bow Club! 🎀 Use code WELCOME10 for 10% off your first order.")
        return redirect(_safe_next(request))
    return render(request, "accounts/signup.html", {"form": form, "next": request.GET.get("next", "")})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You've been signed out. See you soon ♡")
    return redirect("shop:home")


@login_required
def account(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    orders = list(user.orders.prefetch_related("items").all())
    counted = [o for o in orders if o.status != "cancelled"]
    spent = sum((o.total for o in counted), Decimal("0"))
    blossoms = int(spent // 10)
    tier = [name for threshold, name in BLOSSOM_TIERS if blossoms >= threshold][-1]
    notes, seen = [], set()
    for o in orders:
        if o.gift_note and o.gift_note not in seen:
            seen.add(o.gift_note)
            notes.append(o)
    status_filter = request.GET.get("status", "all")
    shown = orders
    if status_filter == "active":
        shown = [o for o in orders if o.is_active_order]
    elif status_filter == "delivered":
        shown = [o for o in orders if o.status == "delivered"]
    return render(request, "accounts/account.html", {
        "profile": profile,
        "orders": shown,
        "order_total": len(orders),
        "active_count": sum(1 for o in orders if o.is_active_order),
        "delivered_count": sum(1 for o in orders if o.status == "delivered"),
        "keepsakes": sum(o.item_count for o in counted),
        "spent": spent,
        "blossoms": blossoms,
        "tier": tier,
        "next_reward": NEXT_REWARD,
        "reward_progress": min(int(blossoms / NEXT_REWARD * 100), 100),
        "blossoms_to_go": max(NEXT_REWARD - blossoms, 0),
        "addresses": user.addresses.all(),
        "saved_notes": notes[:3],
        "status_filter": status_filter,
        "address_form": AddressForm(initial={"recipient_name": user.get_full_name(), "phone": profile.phone}),
        "profile_form": ProfileForm(initial={"full_name": user.get_full_name(), "phone": profile.phone}),
        "initials": "".join(part[0] for part in (user.get_full_name() or user.email or "J").split()[:2]).upper(),
    })


@login_required
@require_POST
def profile_update(request):
    form = ProfileForm(request.POST)
    if form.is_valid():
        first, _, last = form.cleaned_data["full_name"].strip().partition(" ")
        request.user.first_name, request.user.last_name = first, last
        request.user.save(update_fields=["first_name", "last_name"])
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.phone = form.cleaned_data["phone"]
        profile.save()
        messages.success(request, "Profile updated ♡")
    else:
        messages.error(request, "Please enter your name and a valid 10-digit mobile number.")
    return redirect("accounts:account")


@login_required
@require_POST
def address_add(request):
    form = AddressForm(request.POST)
    if form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if address.is_default or not request.user.addresses.exists():
            request.user.addresses.update(is_default=False)
            address.is_default = True
        address.save()
        messages.success(request, f"Saved {address.recipient_name}'s address ♡")
    else:
        errors = "; ".join(f"{form.fields[f].label or f}: {e[0]}" for f, e in form.errors.items())
        messages.error(request, f"Couldn't save that address — {errors}")
    return redirect("/account/#addresses")


@login_required
@require_POST
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    messages.info(request, "Address removed.")
    return redirect("/account/#addresses")
