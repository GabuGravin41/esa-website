def manage_sites(request):
    """Admin view to manage submitted resource sites"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to manage sites.")
        return redirect('more_sites')
        # Get sites grouped by status
    pending_sites = ExternalSite.objects.filter(is_approved=False).order_by('-created_at')
    approved_sites = ExternalSite.objects.filter(is_approved=True).order_by('site_type', 'name')
    rejected_sites = ExternalSite.objects.filter(is_approved=False, is_rejected=True).order_by('-created_at')
    
   
    
    context = {
        'pending_sites': pending_sites,
        'approved_sites': approved_sites,
        'rejected_sites': rejected_sites,
        'title': 'Manage External Sites'
    }
    
    return render(request, 'core/manage_sites.html', context)

def more_sites(request):
    """Render the More Sites page with links to other relevant engineering sites"""
    # Fetch approved external sites grouped by type
    university_clubs = ExternalSite.objects.filter(site_type='university', is_approved=True)
    community_links = ExternalSite.objects.filter(site_type='community', is_approved=True)
    partner_sites = ExternalSite.objects.filter(site_type='partner', is_approved=True)
    
    context = {
        'title': 'Engineering Resources & Links',
        'university_clubs': university_clubs,
        'community_links': community_links,
        'sites': partner_sites
    }
    return render(request, 'core/more_sites.html', context)

def approve_site(request, site_id):
    """Approve a submitted site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to approve sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        site = get_object_or_404(ExternalSite, id=site_id)
        site.is_approved = True
        site.is_rejected = False
        site.save()
        
        messages.success(request, f"Site '{site.name}' has been approved.")
    return redirect('manage_sites')

def reject_site(request, site_id):
    """Reject a submitted site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to reject sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        site = get_object_or_404(ExternalSite, id=site_id)
        site.is_approved = False
        site.is_rejected = True
        site.save()
        
        messages.success(request, f"Site '{site.name}' has been rejected.")
    
    return redirect('manage_sites')


@login_required
def delete_site(request, site_id):
    """Delete a site entirely"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to delete sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        site = get_object_or_404(ExternalSite, id=site_id)
        site_name = site.name
        site.delete()
        
        messages.success(request, f"Site '{site_name}' has been deleted.")
    
    return redirect('manage_sites')

@login_required
def edit_site(request, site_id):
    """Edit an existing site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to edit sites.")
        return redirect('more_sites')
    
    site = get_object_or_404(ExternalSite, id=site_id)
    
    if request.method == 'POST':
        site.name = request.POST.get('name')
        site.url = request.POST.get('url')
        site.description = request.POST.get('description')
        site.site_type = request.POST.get('site_type')
        site.icon = request.POST.get('icon')
        site.save()
        
        messages.success(request, f"Site '{site.name}' has been updated.")
        return redirect('manage_sites')
    
    return render(request, 'core/edit_site.html', {
        'site': site,
        'title': f'Edit Site: {site.name}'
    })

@login_required
def admin_add_site(request):
    """Admin function to directly add a new site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to add sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        url = request.POST.get('url')
        description = request.POST.get('description')
        site_type = request.POST.get('site_type')
        icon = request.POST.get('icon')
        
        if name and url and description and site_type:
            # Create the site (automatically approved)
            site = ExternalSite(
                name=name,
                url=url,
                description=description,
                site_type=site_type,
                icon=icon,
                added_by=request.user,
                is_approved=True
            )
            site.save()
            
            messages.success(request, f"Site '{name}' has been added successfully.")
            return redirect('manage_sites')
        else:
            messages.error(request, "Please fill in all required fields.")
            return redirect('manage_sites')
    
    # This should not normally be reached directly
    return redirect('manage_sites')
