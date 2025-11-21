# Quick Membership Activation Guide

## TL;DR - Activate Members Now

### Option 1: Admin Panel (Easiest)
1. Go to: `https://your-site.com/admin/core/userprofile/`
2. Check the boxes next to users you want to activate
3. Select "Activate membership for selected users" from Actions dropdown
4. Click "Go"
5. ✅ Done! Users now have active 1-year memberships

### Option 2: Command Line
```bash
python manage.py activate_member username_or_email
```

## What Just Got Fixed

### The Problem
- Activating users in admin didn't actually work
- Users showed "inactive" even after toggling membership status
- No Membership records were being created/linked

### The Fix
- Admin now creates Membership records if they don't exist
- Activation properly syncs UserProfile ↔ Membership
- Generates membership numbers automatically
- Sets proper expiry dates (1 year)

## Deploy to Render

Set these environment variables in Render dashboard:
```
DEBUG=false
ENABLE_DEBUG_TOOLBAR=false
```

Then redeploy. The `djdt` error will be gone.

## Verify It Works

After activating a user, check:

1. **In Admin Panel:**
   - User Profile → Membership Status = "Active" ✅
   - Membership Number shows (e.g., "ESA2024001") ✅
   - Expiry Date is ~1 year from now ✅

2. **In Django Shell:**
```python
from django.contrib.auth.models import User
user = User.objects.get(username='testuser')
print(user.profile.membership_status)  # Should print: active
print(user.profile.membership_expiry)   # Should print: date 1 year from now
```

## Troubleshooting

### "User has no profile"
Run:
```bash
python manage.py shell
from django.contrib.auth.models import User
from core.models import UserProfile

user = User.objects.get(username='problematic_user')
UserProfile.objects.create(
    user=user,
    student_id=f"USER{user.id:04d}",
    department="Not specified",
    year_of_study=1
)
```

### "Still showing inactive"
1. Make sure you saved changes in admin
2. Try the management command: `python manage.py activate_member username`
3. Check for errors in terminal/logs

### "Connection error" when loading site
You need to restart your Django server to load the fixed middleware:
```bash
# Stop server (Ctrl+C)
# Clear cache
python manage.py clearsessions
# Start again
python manage.py runserver
```

## Need More Help?

Full details in `DEPLOYMENT_FIXES.md`

