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
