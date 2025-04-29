// Archivo: static/js/menu.js

document.addEventListener('DOMContentLoaded', function() {
    // Obtener la URL actual
    const currentPath = window.location.pathname;
    
    // Buscar todos los elementos de menú
    const menuItems = document.querySelectorAll('.sidebar-menu a');
    
    // Función para comprobar si una ruta está contenida en otra
    function isPathContained(path, containerPath) {
        // Eliminar parámetros de consulta si existen
        path = path.split('?')[0];
        containerPath = containerPath.split('?')[0];
        
        // Comprobar si la ruta completa coincide
        if (path === containerPath) return true;
        
        // Comprobar si la ruta actual es una subruta de la ruta del menú
        // Por ejemplo, /clientes/1/editar debería resaltar el menú /clientes
        const pathParts = path.split('/').filter(Boolean);
        const containerParts = containerPath.split('/').filter(Boolean);
        
        if (containerParts.length === 0) return false;
        
        return pathParts[0] === containerParts[0];
    }
    
    // Recorrer todos los elementos del menú y resaltar el activo
    menuItems.forEach(item => {
        const href = item.getAttribute('href');
        
        if (href && isPathContained(currentPath, href)) {
            // Agregar clase active
            item.classList.add('active');
            
            // Si está dentro de un submenú, expandir el elemento padre
            const parentLi = item.closest('li.has-submenu');
            if (parentLi) {
                parentLi.classList.add('active');
                const submenu = parentLi.querySelector('.submenu');
                if (submenu) {
                    submenu.style.display = 'block';
                }
            }
        }
    });
});