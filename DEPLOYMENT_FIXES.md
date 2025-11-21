# Deployment Fixes Summary

## Issues Fixed

### 1. Django Debug Toolbar Error (`djdt` namespace not registered)

**Problem:** Debug Toolbar was active in production but its URLs weren't registered, causing NoReverseMatch errors.

**Solution:**
- Added `ENABLE_DEBUG_TOOLBAR` flag in `settings.py` (separate from `DEBUG`)
- Conditionally include Debug Toolbar in `INSTALLED_APPS` and `MIDDLEWARE` only when flag is `True`
- Added safety check to remove toolbar middleware if flag is `False`
- Added Debug Toolbar URLs to `urls.py` only when flag is enabled

**Required Environment Variables for Production (Render):**
```bash
DEBUG=false
ENABLE_DEBUG_TOOLBAR=false
```

**For Local Development:**
```bash
DEBUG=true
ENABLE_DEBUG_TOOLBAR=true  # Only if you want the debug toolbar
```

### 2. Middleware Connection NameError

**Problem:** `PerformanceMonitoringMiddleware` referenced `connection` without importing it.

**Solution:**
- Added `from django.db import connection` import
- Wrapped query counting in `if settings.DEBUG:` checks for safety
- Used `getattr(connection, 'queries', [])` for safe access

**Files Modified:**
- `core/middleware.py`

### 3. Membership Activation Not Working

**Problem:** Admin panel membership activation wasn't syncing properly because it only looked for memberships with `status='completed'`, and didn't create memberships if none existed.

**Solution:**

#### In `core/admin.py` - UserProfileAdmin:

**save_model():**
- Now finds ANY membership (not just completed ones)
- Creates a new membership if none exists when activating
- Properly syncs membership number and expiry date

**activate_membership() action:**
- Finds or creates membership for each profile
- Activates existing memberships or creates new ones
- Sets proper dates, status, and membership numbers
- Shows count of actually activated memberships

**deactivate_membership() action:**
- Sets status to 'expired' in addition to is_active=False

#### In `core/admin.py` - MembershipAdmin:
- Already had proper activate/deactivate actions
- These work correctly when used from the Membership admin panel

## How to Activate Memberships

### Method 1: Django Admin Panel (User Profiles)

1. Go to: `/admin/core/userprofile/`
2. Select users to activate
3. Actions dropdown → "Activate membership for selected users"
4. Click "Go"

**What happens:**
- Profile membership_status → 'active'
- Profile membership_expiry → 1 year from now
- Creates or activates Membership record
- Generates membership number if missing
- Syncs all data between Profile and Membership

### Method 2: Django Admin Panel (Memberships)

1. Go to: `/admin/core/membership/`
2. Select memberships
3. Actions dropdown → "Activate selected memberships"
4. Click "Go"

**What happens:**
- Calls `membership.activate()` method
- Updates linked UserProfile automatically

### Method 3: Management Command (CLI)

```bash
# Activate by username
python manage.py activate_member john_doe

# Activate by email
python manage.py activate_member user@example.com

# Specify custom plan and amount
python manage.py activate_member john_doe --plan first_year --amount 150
```

**What happens:**
- Finds or creates membership
- Activates it with 1-year expiry
- Syncs UserProfile
- Shows detailed output

## Verification

To verify membership is active:

### Check in Django Shell:
```python
from django.contrib.auth.models import User
from core.models import Membership, UserProfile

user = User.objects.get(username='your_username')
profile = user.profile
membership = Membership.objects.filter(user=user).first()

print(f"Profile Status: {profile.membership_status}")
print(f"Profile Expiry: {profile.membership_expiry}")
print(f"Membership Active: {membership.is_active if membership else 'No membership'}")
print(f"Membership Status: {membership.status if membership else 'No membership'}")
```

### Check in Admin Panel:
1. Go to User Profiles admin
2. Look for "Membership Status" column
3. Should show "Active" with green checkmark
4. Click on user to see membership details

## Database Models

### UserProfile
- `membership_status`: 'inactive', 'active', 'expired', 'suspended'
- `membership_expiry`: Date when membership expires
- `membership_number`: Unique membership ID (e.g., "ESA2024001")

### Membership
- `is_active`: Boolean flag
- `status`: 'pending', 'completed', 'cancelled', 'expired'
- `start_date`: When membership started
- `end_date`: When membership expires (1 year from start)
- `membership_number`: Matches UserProfile.membership_number
- `payment_verified`: Admin verified payment

## Important Notes

1. **Two-Way Sync**: Changes in UserProfile admin OR Membership admin will sync to the other
2. **Automatic Creation**: If user has no Membership record, one is created when activating
3. **Membership Numbers**: Auto-generated in format "ESA{YEAR}{COUNTER}" (e.g., ESA2024001)
4. **Default Duration**: 1 year from activation date
5. **Manual Payments**: Use payment_method='manual' for admin-activated memberships

## Deployment Checklist

Before deploying to Render:

- [ ] Set `DEBUG=false` in Render environment variables
- [ ] Set `ENABLE_DEBUG_TOOLBAR=false` in Render environment variables
- [ ] Clear Python cache: `python manage.py clearsessions`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Test membership activation in staging first
- [ ] Verify no `djdt` errors in logs

## Files Modified

1. `puddle/settings.py` - Added ENABLE_DEBUG_TOOLBAR, conditional toolbar loading
2. `puddle/urls.py` - Conditional Debug Toolbar URLs
3. `core/middleware.py` - Fixed connection import, guarded query counting
4. `core/admin.py` - Enhanced membership activation logic in UserProfileAdmin
5. `core/management/commands/activate_member.py` - New CLI tool for activation

## Testing

After deployment, test:

1. Visit homepage - should load without djdt errors
2. Activate a test user's membership in admin
3. Verify membership status shows as active
4. Check that membership number is generated
5. Verify expiry date is set to 1 year from now

