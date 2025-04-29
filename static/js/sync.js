// /static/js/sync.js

/**
 * Lógica para sincronización de datos offline/online
 */

// Configuración
const SYNC_INTERVAL = 30000; // Intervalo de reintento de sincronización (30 segundos)
const PENDING_DATA_KEY = "pendingSyncData"; // Clave en localStorage

// Elementos UI
let syncButton = null;
let syncIcon = null;
let syncBadge = null;

// Estado
let isOnline = navigator.onLine;
let isSyncing = false;
let pendingData = [];
let syncTimer = null;

// Inicialización
document.addEventListener("DOMContentLoaded", function() {
    syncButton = document.getElementById("sync-button");
    if (!syncButton) return; // Salir si el botón no existe (ej. no autenticado)
    
    syncIcon = syncButton.querySelector("i");
    syncBadge = syncButton.querySelector(".badge");

    // Cargar datos pendientes
    loadPendingData();

    // Actualizar UI inicial
    updateSyncStatusUI();

    // Escuchar cambios de conexión
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Iniciar intento de sincronización si hay datos pendientes y estamos online
    if (isOnline && pendingData.length > 0) {
        scheduleSync();
    }

    // Evento click en el botón (puede forzar sincronización o mostrar estado)
    syncButton.addEventListener("click", function() {
        if (isOnline && pendingData.length > 0 && !isSyncing) {
            console.log("Forzando sincronización...");
            syncPendingData();
        }
    });
});

// Cargar datos pendientes desde localStorage
function loadPendingData() {
    const storedData = localStorage.getItem(PENDING_DATA_KEY);
    if (storedData) {
        try {
            pendingData = JSON.parse(storedData);
            if (!Array.isArray(pendingData)) {
                pendingData = [];
            }
        } catch (e) {
            console.error("Error cargando datos pendientes:", e);
            pendingData = [];
            localStorage.removeItem(PENDING_DATA_KEY); // Limpiar si está corrupto
        }
    }
    console.log(`Datos pendientes cargados: ${pendingData.length}`);
}

// Guardar datos pendientes en localStorage
function savePendingData() {
    try {
        localStorage.setItem(PENDING_DATA_KEY, JSON.stringify(pendingData));
    } catch (e) {
        console.error("Error guardando datos pendientes:", e);
        // Considerar una estrategia de respaldo o notificación al usuario
    }
}

// Manejar cambio a estado online
function handleOnline() {
    console.log("Conexión recuperada.");
    isOnline = true;
    updateSyncStatusUI();
    if (pendingData.length > 0) {
        scheduleSync(); // Intentar sincronizar ahora
    }
}

// Manejar cambio a estado offline
function handleOffline() {
    console.log("Conexión perdida.");
    isOnline = false;
    isSyncing = false; // Detener sincronización si estaba en curso
    clearTimeout(syncTimer); // Cancelar reintentos programados
    updateSyncStatusUI();
}

// Actualizar la interfaz del botón de sincronización
function updateSyncStatusUI() {
    if (!syncButton || !syncIcon || !syncBadge) return;

    syncIcon.classList.remove("fa-check-circle", "fa-exclamation-triangle", "fa-sync-alt", "sync-spinning");
    syncButton.classList.remove("btn-success", "btn-warning", "btn-secondary", "btn-primary");
    syncButton.disabled = false;
    let tooltipTitle = "";

    if (isOnline) {
        if (isSyncing) {
            syncIcon.classList.add("fa-sync-alt", "sync-spinning");
            syncButton.classList.add("btn-primary");
            tooltipTitle = "Sincronizando datos...";
            syncBadge.style.display = "none";
        } else if (pendingData.length > 0) {
            syncIcon.classList.add("fa-exclamation-triangle");
            syncButton.classList.add("btn-warning");
            syncBadge.textContent = pendingData.length;
            syncBadge.style.display = "block";
            tooltipTitle = `${pendingData.length} operaciones pendientes de sincronizar. Haz clic para intentar ahora.`;
        } else {
            syncIcon.classList.add("fa-check-circle");
            syncButton.classList.add("btn-success");
            syncBadge.style.display = "none";
            tooltipTitle = "Datos sincronizados.";
        }
    } else {
        syncIcon.classList.add("fa-exclamation-triangle");
        syncButton.classList.add("btn-secondary");
        syncButton.disabled = true; // Deshabilitar botón offline
        if (pendingData.length > 0) {
            syncBadge.textContent = pendingData.length;
            syncBadge.style.display = "block";
            tooltipTitle = `Sin conexión. ${pendingData.length} operaciones pendientes.`;
        } else {
            syncBadge.style.display = "none";
            tooltipTitle = "Sin conexión.";
        }
    }
    
    // Actualizar tooltip (requiere reinicializar si se usa Bootstrap)
    const tooltipInstance = bootstrap.Tooltip.getInstance(syncButton);
    if (tooltipInstance) {
        tooltipInstance.setContent({ ".tooltip-inner": tooltipTitle });
    } else {
        syncButton.setAttribute("data-bs-original-title", tooltipTitle);
        new bootstrap.Tooltip(syncButton); // Crear si no existe
    }
}

// Programar un intento de sincronización
function scheduleSync(delay = 500) { // Pequeño delay inicial
    clearTimeout(syncTimer);
    if (!isOnline || isSyncing || pendingData.length === 0) {
        return;
    }
    syncTimer = setTimeout(syncPendingData, delay);
}

// Función principal para sincronizar datos pendientes
async function syncPendingData() {
    if (!isOnline || isSyncing || pendingData.length === 0) {
        console.log("Sincronización omitida (offline, ya sincronizando o sin datos).");
        return;
    }

    isSyncing = true;
    updateSyncStatusUI();
    console.log(`Iniciando sincronización de ${pendingData.length} elementos...`);

    // Tomar una copia de los datos pendientes para procesar
    const dataToSync = [...pendingData];
    let successfullySyncedIndices = [];

    try {
        // Enviar los datos al backend (ejemplo: un endpoint /api/sync)
        // El backend debería procesar cada operación y devolver cuáles fueron exitosas
        const response = await fetch("/api/sync", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                // Incluir token CSRF si es necesario
                // "X-CSRFToken": getCookie("csrftoken") 
            },
            body: JSON.stringify({ operations: dataToSync })
        });

        if (!response.ok) {
            // Error general del servidor
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success && Array.isArray(result.processed_indices)) {
            // Marcar los elementos que el backend confirmó como procesados
            successfullySyncedIndices = result.processed_indices;
            console.log(`Sincronización parcial/total exitosa. ${successfullySyncedIndices.length} elementos procesados.`);
            
            // Eliminar elementos sincronizados de la lista original (pendingData)
            // Es importante hacerlo de forma segura, iterando inversamente o filtrando
            pendingData = pendingData.filter((_, index) => !successfullySyncedIndices.includes(index));
            savePendingData(); // Guardar la lista actualizada
            
        } else {
            // El backend devolvió un error específico o formato inesperado
            console.error("Respuesta de sincronización inválida:", result);
            throw new Error(result.message || "Error desconocido durante la sincronización.");
        }

    } catch (error) {
        console.error("Error durante la sincronización:", error);
        // No eliminar datos pendientes si hubo error
        // Programar reintento
        scheduleSync(SYNC_INTERVAL);
    } finally {
        isSyncing = false;
        updateSyncStatusUI();
        
        // Si aún quedan datos pendientes y estamos online, programar otro intento
        if (isOnline && pendingData.length > 0) {
            console.log(`Aún quedan ${pendingData.length} elementos pendientes. Reintentando en ${SYNC_INTERVAL / 1000}s...`);
            scheduleSync(SYNC_INTERVAL);
        }
    }
}

/**
 * Función para agregar una operación a la cola de sincronización.
 * Llamar a esta función desde otras partes de la app cuando se realiza una acción offline.
 * 
 * @param {string} type - Tipo de operación (ej. "crear_abono", "actualizar_cliente")
 * @param {object} payload - Datos necesarios para la operación
 * @param {string} [entityId] - ID local o temporal de la entidad afectada (opcional)
 */
function addPendingOperation(type, payload, entityId = null) {
    const operation = {
        id: Date.now() + "-" + Math.random().toString(36).substring(2, 9), // ID único
        type: type,
        payload: payload,
        timestamp: new Date().toISOString(),
        entityId: entityId // Para posible referencia local
    };

    pendingData.push(operation);
    savePendingData();
    updateSyncStatusUI();

    // Si estamos online, intentar sincronizar pronto
    if (isOnline) {
        scheduleSync();
    }
    
    console.log("Operación añadida a la cola:", operation);
}

// Ejemplo de cómo obtener CSRF token si se usa Django/Flask-WTF
/*
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
*/

