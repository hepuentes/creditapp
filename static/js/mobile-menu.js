// Archivo: static/js/mobile-menu.js

document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
    const sidebar = document.querySelector('.sidebar');
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    // Función para abrir/cerrar el menú
    function toggleMenu() {
        sidebar.classList.toggle('active');
        sidebarOverlay.classList.toggle('active');
        
        // Evitar el desplazamiento del body cuando el menú está abierto
        if (sidebar.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }
    
    // Asignar evento al botón de hamburguesa
    if (menuToggle) {
        menuToggle.addEventListener('click', toggleMenu);
    }
    
    // Cerrar el menú al hacer clic fuera
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleMenu);
    }
    
    // Cerrar el menú al hacer clic en un elemento
    const menuLinks = document.querySelectorAll('.sidebar a');
    menuLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                toggleMenu();
            }
        });
    });
});