document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  
  // Toggle sidebar
  mobileMenuToggle.addEventListener('click', function() {
    sidebar.classList.toggle('mobile-open');
    sidebarOverlay.classList.toggle('active');
  });
  
  // Close sidebar when clicking overlay
  sidebarOverlay.addEventListener('click', function() {
    sidebar.classList.remove('mobile-open');
    sidebarOverlay.classList.remove('active');
  });
  
  // Close sidebar when clicking on a nav link (mobile)
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', function() {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('mobile-open');
        sidebarOverlay.classList.remove('active');
      }
    });
  });
});