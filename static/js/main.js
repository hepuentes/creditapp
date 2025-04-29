// /static/js/main.js

/**
 * Funciones principales para la aplicación
 */

// Variables globales para el carrito de compras
let carritoItems = [];
let clienteSeleccionado = null;

// Inicializar al cargar la página
document.addEventListener("DOMContentLoaded", function() {
    // Inicializar menú (incluye activación según ruta)
    initMenu();
    
    // Inicializar carrito si estamos en la página de crear crédito
    initCarrito();
    
    // Inicializar búsqueda de clientes
    initClienteSearch();
    
    // Inicializar búsqueda de productos
    initProductoSearch();
    
    // Aplicar formato a elementos monetarios (llamado desde formatters.js)
    // aplicarFormatoMoneda(); // Ya se llama desde formatters.js al inicializar
    
    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll("[data-bs-toggle=\"tooltip\"]"));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar datepickers si existen (si se usa una librería externa)
    // initDatepickers(); 
    
    // Inicializar eventos para período de pago (si es necesario)
    // initPeriodoPago();
    
    // Lógica para mostrar/ocultar resultados de búsqueda
    initBusquedaDropdowns();
});

// Inicializar menú y su comportamiento
function initMenu() {
    const sidebarCollapse = document.getElementById("sidebarCollapse");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.querySelector(".overlay");
    const toggleSidebar = document.getElementById("toggleSidebar");

    // Menú móvil: Abrir/cerrar con botón y overlay
    if (sidebarCollapse && sidebar && overlay) {
        sidebarCollapse.addEventListener("click", function () {
            sidebar.classList.toggle("active");
            overlay.classList.toggle("active");
        });
        overlay.addEventListener("click", function () {
            sidebar.classList.remove("active");
            overlay.classList.remove("active");
        });
    }

    // Menú escritorio: Colapsar/expandir y guardar preferencia
    if (toggleSidebar && sidebar) {
        toggleSidebar.addEventListener("click", function() {
            sidebar.classList.toggle("collapsed");
            localStorage.setItem("sidebarCollapsed", sidebar.classList.contains("collapsed"));
        });
        // Cargar preferencia guardada
        if (localStorage.getItem("sidebarCollapsed") === "true") {
            sidebar.classList.add("collapsed");
        }
    }
    
    // Activar elemento del menú según la ruta actual
    activarMenuSegunRuta();
}

// Corregir problema de activación doble en el menú
function activarMenuSegunRuta() {
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll("#sidebar ul li[data-path]"); // Usar data-path
    
    // Primero, eliminar todas las clases active
    menuItems.forEach(item => {
        item.classList.remove("active");
    });

    let bestMatch = null;
    let bestMatchLength = 0;

    menuItems.forEach(item => {
        const itemPath = item.getAttribute("data-path");
        if (!itemPath) return;

        // Coincidencia exacta para la raíz
        if (itemPath === "/" && currentPath === "/") {
            // Considerar la raíz como una coincidencia válida
             if (itemPath.length >= bestMatchLength) { // Usar >= para priorizar la raíz si es la única coincidencia
                 bestMatch = item;
                 bestMatchLength = itemPath.length;
             }
            return; // No retornar aquí, permitir que otras rutas más largas coincidan si es necesario
        }

        // Coincidencia de prefijo para otras rutas (excluyendo la raíz sola)
        if (itemPath !== "/" && currentPath.startsWith(itemPath)) {
            if (itemPath.length > bestMatchLength) {
                bestMatch = item;
                bestMatchLength = itemPath.length;
            }
        }
    });

    // Activar solo el mejor match
    if (bestMatch) {
        bestMatch.classList.add("active");
    } else if (currentPath === "/") { 
        // Caso especial: si no hubo match pero estamos en la raíz, activar el dashboard
        const dashboardItem = document.querySelector("#sidebar ul li[data-path=\"/\"]");
        if (dashboardItem) {
            dashboardItem.classList.add("active");
        }
    }
}


// --- Funciones del Carrito de Compras (para crear_credito.html) ---

function initCarrito() {
    const carritoContainer = document.getElementById("carrito-items");
    if (!carritoContainer) return; // Solo ejecutar en la página correcta

    // Cargar carrito desde localStorage si existe
    const carritoGuardado = localStorage.getItem("carritoItems");
    if (carritoGuardado) {
        try {
            carritoItems = JSON.parse(carritoGuardado);
        } catch (e) {
            console.error("Error al cargar carrito:", e);
            carritoItems = [];
            localStorage.removeItem("carritoItems"); // Limpiar si está corrupto
        }
    }
    actualizarCarritoUI();
    
    // Cargar cliente seleccionado desde localStorage
    const clienteGuardado = localStorage.getItem("clienteSeleccionado");
    if (clienteGuardado) {
        try {
            clienteSeleccionado = JSON.parse(clienteGuardado);
            mostrarInfoClienteSeleccionado();
        } catch (e) {
            console.error("Error al cargar cliente:", e);
            clienteSeleccionado = null;
            localStorage.removeItem("clienteSeleccionado");
        }
    }
}

function agregarAlCarrito(producto) {
    if (!producto || !producto.id || !producto.nombre || producto.precio === undefined) {
        console.error("Producto inválido:", producto);
        return;
    }

    const existente = carritoItems.find(item => item.id === producto.id);
    const precioNumerico = desformatearNumero(producto.precio);

    if (existente) {
        existente.cantidad += 1;
    } else {
        carritoItems.push({
            id: producto.id,
            nombre: producto.nombre,
            precio: precioNumerico, // Guardar como número
            cantidad: 1
        });
    }
    
    actualizarCarritoUI();
    guardarCarritoEnLocalStorage();
}

function eliminarDelCarrito(index) {
    if (index >= 0 && index < carritoItems.length) {
        carritoItems.splice(index, 1);
        actualizarCarritoUI();
        guardarCarritoEnLocalStorage();
    }
}

function cambiarCantidad(index, delta) {
    if (index >= 0 && index < carritoItems.length) {
        carritoItems[index].cantidad += delta;
        if (carritoItems[index].cantidad < 1) {
            carritoItems[index].cantidad = 1; // Mínimo 1
        }
        actualizarCarritoUI();
        guardarCarritoEnLocalStorage();
    }
}

function actualizarCarritoUI() {
    const carritoContainer = document.getElementById("carrito-items");
    const totalElement = document.getElementById("carrito-total");
    const itemsJsonInput = document.getElementById("items_json");
    const montoTotalInput = document.getElementById("monto_total");

    if (!carritoContainer || !totalElement || !itemsJsonInput || !montoTotalInput) return;

    if (carritoItems.length === 0) {
        carritoContainer.innerHTML = 
            `<p class="text-muted text-center my-3">No hay productos seleccionados</p>`;
        totalElement.textContent = formatearNumero(0);
        itemsJsonInput.value = "[]";
        montoTotalInput.value = "0";
        return;
    }

    let html = "";
    let total = 0;

    carritoItems.forEach((item, index) => {
        const subtotal = item.precio * item.cantidad;
        total += subtotal;
        html += `
            <div class="carrito-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="fw-bold">${item.nombre}</span><br>
                    <small class="text-muted">${formatearNumero(item.precio)} x ${item.cantidad}</small>
                </div>
                <div class="d-flex align-items-center">
                    <span class="fw-bold me-3 formato-moneda">${formatearNumero(subtotal)}</span>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-secondary" onclick="cambiarCantidad(${index}, -1)">-</button>
                        <button type="button" class="btn btn-outline-secondary" onclick="cambiarCantidad(${index}, 1)">+</button>
                        <button type="button" class="btn btn-outline-danger" onclick="eliminarDelCarrito(${index})">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    carritoContainer.innerHTML = html;
    totalElement.textContent = formatearNumero(total);
    // Enviar solo ID, cantidad y precio (asegurando que el precio sea número)
    itemsJsonInput.value = JSON.stringify(carritoItems.map(item => ({ 
        id: item.id, 
        cantidad: item.cantidad, 
        precio: Number(item.precio) // Asegurar que precio sea número
    })));
    montoTotalInput.value = total;
    
    // Reaplicar formato a los subtotales recién añadidos
    aplicarFormatoMoneda(); 
}

function guardarCarritoEnLocalStorage() {
    localStorage.setItem("carritoItems", JSON.stringify(carritoItems));
}

function limpiarCarrito() {
    carritoItems = [];
    clienteSeleccionado = null;
    actualizarCarritoUI();
    localStorage.removeItem("carritoItems");
    localStorage.removeItem("clienteSeleccionado");
    // Limpiar campos del formulario relacionados
    const clienteSearchInput = document.getElementById("cliente-search");
    const clienteIdInput = document.getElementById("cliente_id");
    if(clienteSearchInput) clienteSearchInput.value = "";
    if(clienteIdInput) clienteIdInput.value = "";
    mostrarInfoClienteSeleccionado(); // Ocultar info del cliente
}

// Limpiar carrito al enviar el formulario con éxito
const formCrearCredito = document.getElementById("form-crear-credito");
if (formCrearCredito) {
    formCrearCredito.addEventListener("submit", function(event) {
        // Validar que haya cliente y productos antes de limpiar
        const clienteId = document.getElementById("cliente_id").value;
        if (!clienteId || carritoItems.length === 0) {
            // Si falta cliente o productos, la validación del backend debería fallar
            // No limpiamos el carrito aquí
            return; 
        }
        
        // Asumiendo que el envío es exitoso si pasa la validación básica
        // Una mejor aproximación sería limpiar después de una respuesta exitosa del servidor
        // Usamos un pequeño delay para permitir que el formulario se envíe
        setTimeout(limpiarCarrito, 500); 
    });
}

// --- Funciones de Búsqueda (Clientes y Productos) ---

function initClienteSearch() {
    const searchInput = document.getElementById("cliente-search");
    const resultsContainer = document.getElementById("cliente-results");
    const clienteIdInput = document.getElementById("cliente_id");

    if (!searchInput || !resultsContainer || !clienteIdInput) return;

    searchInput.addEventListener("input", function() {
        const query = this.value.trim();
        // Limpiar cliente seleccionado si se modifica la búsqueda
        if (clienteSeleccionado && clienteSeleccionado.nombre !== query) {
            clienteSeleccionado = null;
            clienteIdInput.value = "";
            mostrarInfoClienteSeleccionado();
            localStorage.removeItem("clienteSeleccionado");
        }
        
        if (query.length < 2) {
            resultsContainer.innerHTML = "";
            resultsContainer.style.display = "none";
            return;
        }

        fetch(`/api/clientes/buscar?q=${encodeURIComponent(query)}`)
            .then(response => response.ok ? response.json() : Promise.reject("Error fetching clientes"))
            .then(data => {
                mostrarResultadosBusqueda(data, resultsContainer, seleccionarCliente);
            })
            .catch(error => {
                console.error("Error buscando clientes:", error);
                resultsContainer.innerHTML = `<div class="search-item text-danger">Error al buscar</div>`;
                resultsContainer.style.display = "block";
            });
    });
}

function initProductoSearch() {
    const searchInput = document.getElementById("producto-search");
    const resultsContainer = document.getElementById("producto-results");

    if (!searchInput || !resultsContainer) return;

    searchInput.addEventListener("input", function() {
        const query = this.value.trim();
        if (query.length < 2) {
            resultsContainer.innerHTML = "";
            resultsContainer.style.display = "none";
            return;
        }

        fetch(`/api/productos/buscar?q=${encodeURIComponent(query)}`)
            .then(response => response.ok ? response.json() : Promise.reject("Error fetching productos"))
            .then(data => {
                mostrarResultadosBusqueda(data, resultsContainer, seleccionarProducto);
            })
            .catch(error => {
                console.error("Error buscando productos:", error);
                resultsContainer.innerHTML = `<div class="search-item text-danger">Error al buscar</div>`;
                resultsContainer.style.display = "block";
            });
    });
}

function mostrarResultadosBusqueda(data, container, selectCallback) {
    container.innerHTML = "";
    if (!data || data.length === 0) {
        container.innerHTML = `<div class="search-item text-muted">No se encontraron resultados</div>`;
        container.style.display = "block";
        return;
    }

    data.forEach(item => {
        const div = document.createElement("div");
        div.className = "search-item";
        // Adaptar la visualización según si es cliente o producto
        if (item.documento) { // Es cliente
            div.innerHTML = `<strong>${item.nombre}</strong><br><small class="text-muted">${item.documento}</small>`;
        } else { // Es producto
             div.innerHTML = `
                <div class="d-flex justify-content-between">
                    <strong>${item.nombre}</strong>
                    <span class="formato-moneda">${formatearNumero(item.precio)}</span>
                </div>
                <small class="text-muted">Stock: ${item.stock !== null ? item.stock : "N/A"}</small>
            `;
        }
        
        div.addEventListener("click", () => {
            selectCallback(item);
            container.innerHTML = "";
            container.style.display = "none";
            // Limpiar input de búsqueda después de seleccionar
            if (container.id === "cliente-results") {
                // No limpiar input de cliente, ya se actualiza en seleccionarCliente
            } else {
                 document.getElementById("producto-search").value = ""; // Limpiar input de producto
            }
        });
        container.appendChild(div);
    });
    container.style.display = "block";
    aplicarFormatoMoneda(); // Aplicar formato a precios en resultados de producto
}

function seleccionarCliente(cliente) {
    clienteSeleccionado = cliente;
    document.getElementById("cliente_id").value = cliente.id;
    document.getElementById("cliente-search").value = cliente.nombre; // Mantener nombre en input
    mostrarInfoClienteSeleccionado();
    localStorage.setItem("clienteSeleccionado", JSON.stringify(cliente));
    // Ocultar resultados después de seleccionar
    const resultsContainer = document.getElementById("cliente-results");
    if (resultsContainer) {
        resultsContainer.style.display = "none";
    }
}

function seleccionarProducto(producto) {
    agregarAlCarrito(producto);
    document.getElementById("producto-search").value = ""; // Limpiar input
     // Ocultar resultados después de seleccionar
    const resultsContainer = document.getElementById("producto-results");
    if (resultsContainer) {
        resultsContainer.style.display = "none";
    }
}

function mostrarInfoClienteSeleccionado() {
    const infoDiv = document.getElementById("cliente-seleccionado-info");
    const nombreSpan = document.getElementById("cliente-nombre");
    const docSpan = document.getElementById("cliente-documento");
    const searchInput = document.getElementById("cliente-search");

    if (!infoDiv || !nombreSpan || !docSpan || !searchInput) return;

    if (clienteSeleccionado) {
        nombreSpan.textContent = clienteSeleccionado.nombre;
        docSpan.textContent = `Doc: ${clienteSeleccionado.documento}`;
        infoDiv.style.display = "block";
        searchInput.value = clienteSeleccionado.nombre; // Asegurar que el input muestre el nombre
    } else {
        infoDiv.style.display = "none";
        nombreSpan.textContent = "";
        docSpan.textContent = "";
        // No limpiar el input aquí, se maneja en el evento 'input'
    }
}

// Cerrar dropdowns de búsqueda al hacer clic fuera
function initBusquedaDropdowns() {
     document.addEventListener("click", function(event) {
        const clienteResults = document.getElementById("cliente-results");
        const productoResults = document.getElementById("producto-results");
        const clienteSearch = document.getElementById("cliente-search");
        const productoSearch = document.getElementById("producto-search");

        // Cerrar si se hace clic fuera del input Y fuera del contenedor de resultados
        if (clienteResults && clienteSearch && !clienteSearch.contains(event.target) && !clienteResults.contains(event.target)) {
            clienteResults.style.display = "none";
        }
        if (productoResults && productoSearch && !productoSearch.contains(event.target) && !productoResults.contains(event.target)) {
            productoResults.style.display = "none";
        }
    });
}

