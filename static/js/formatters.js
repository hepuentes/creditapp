// /static/js/formatters.js

/**
 * Formatea un número para mostrar separadores de miles (puntos)
 * @param {number|string} numero - El número a formatear
 * @param {number} decimales - Número de decimales a mostrar (por defecto 0)
 * @returns {string} El número formateado
 */
function formatearNumero(numero, decimales = 0) {
    if (numero === null || numero === undefined || numero === "") {
        return "0"; // O podrías devolver "0,00" si decimales > 0
    }

    // Convertir a número si es string, manejando formato español
    if (typeof numero === "string") {
        numero = numero.replace(/\./g, "").replace(",", "."); // Puntos de miles a nada, coma decimal a punto
        numero = parseFloat(numero);
    }

    // Si no es un número válido, devolver 0 formateado
    if (isNaN(numero)) {
        // Devolver "0" o "0,00" según los decimales
        return (0).toLocaleString("es-ES", {
            minimumFractionDigits: decimales,
            maximumFractionDigits: decimales
        });
    }

    // Formatear usando toLocaleString para es-ES (maneja puntos y comas correctamente)
    return numero.toLocaleString("es-ES", {
        minimumFractionDigits: decimales,
        maximumFractionDigits: decimales
    });
}

/**
 * Desformatea un número con separadores de miles (puntos) y coma decimal
 * @param {string|number} numeroFormateado - El número formateado a convertir
 * @returns {number} El número sin formato (como float)
 */
function desformatearNumero(numeroFormateado) {
    if (numeroFormateado === null || numeroFormateado === undefined) {
        return 0;
    }

    // Si ya es un número, devolverlo
    if (typeof numeroFormateado === "number") {
        return numeroFormateado;
    }

    // Convertir a string para procesar
    const numStr = String(numeroFormateado);

    // Eliminar puntos de miles y cambiar coma decimal por punto
    try {
        const numeroLimpio = numStr.replace(/\./g, "").replace(",", ".");
        const numero = parseFloat(numeroLimpio);
        return isNaN(numero) ? 0 : numero;
    } catch (e) {
        console.error("Error al desformatear número:", numeroFormateado, e);
        return 0;
    }
}

/**
 * Aplica formato de moneda a elementos con clase 'formato-moneda'
 */
function aplicarFormatoMoneda() {
    // Aplicar a elementos que no son input
    document.querySelectorAll(".formato-moneda:not(input)").forEach(function(elemento) {
        const contenido = elemento.textContent.trim();
        if (contenido) {
            const decimales = elemento.dataset.decimales ? parseInt(elemento.dataset.decimales) : 0;
            // Solo formatear si el contenido parece un número o ya está formateado
            if (!isNaN(desformatearNumero(contenido))) {
                 elemento.textContent = formatearNumero(contenido, decimales);
            }
        }
    });

    // Aplicar a inputs
    document.querySelectorAll("input.formato-moneda").forEach(function(input) {
        if (!input.dataset.formatoAplicado) {
            input.dataset.formatoAplicado = true;
            const decimales = input.dataset.decimales ? parseInt(input.dataset.decimales) : 0;

            // Formatear valor inicial si existe y no tiene foco
            if (input.value && document.activeElement !== input) {
                 if (!isNaN(desformatearNumero(input.value))) {
                    input.value = formatearNumero(input.value, decimales);
                 }
            }

            // Evento al obtener foco: mostrar sin formato (número crudo)
            input.addEventListener("focus", function() {
                const valor = desformatearNumero(this.value);
                // Mostrar el número crudo (con punto decimal si aplica) o vacío si es 0
                this.value = valor !== 0 ? String(valor).replace(".", ",") : ""; 
                this.select(); 
            });

            // Evento al perder foco: aplicar formato
            input.addEventListener("blur", function() {
                const valor = this.value.trim();
                if (valor) {
                    // Usar desformatear y luego formatear para asegurar consistencia
                    this.value = formatearNumero(desformatearNumero(valor), decimales);
                } else {
                    // Si está vacío, mostrar 0 formateado
                    this.value = formatearNumero(0, decimales);
                }
            });

            // Evento al escribir: permitir solo números y una coma
            input.addEventListener("input", function(e) {
                let valor = this.value;
                // Eliminar caracteres no numéricos excepto la coma
                valor = valor.replace(/[^0-9,]/g, "");
                // Asegurar que solo haya una coma
                const partes = valor.split(",");
                if (partes.length > 2) {
                    valor = partes[0] + "," + partes.slice(1).join("");
                }
                this.value = valor;
            });
        }
    });
}

/**
 * Observa cambios en el DOM para aplicar formato automáticamente
 */
function inicializarFormatoMonedaConObservador() {
    // Aplicar formato inicial
    aplicarFormatoMoneda();

    // Observar cambios en el DOM para aplicar formato a nuevos elementos
    const observador = new MutationObserver(function(mutaciones) {
        let necesitaActualizar = false;
        mutaciones.forEach(function(mutacion) {
            if (mutacion.type === "childList" && mutacion.addedNodes.length > 0) {
                 for (let nodo of mutacion.addedNodes) {
                     if (nodo.nodeType === 1) { 
                         if (nodo.classList && nodo.classList.contains("formato-moneda") || nodo.querySelector(".formato-moneda")) {
                             necesitaActualizar = true;
                             break;
                         }
                     }
                 }
            } else if (mutacion.type === "attributes" && mutacion.attributeName === "class") {
                 if (mutacion.target.classList && mutacion.target.classList.contains("formato-moneda")) {
                    necesitaActualizar = true;
                 }
            }
            // Podríamos añadir observación de cambio de textContent si es necesario
        });

        if (necesitaActualizar) {
            // Usar requestAnimationFrame para asegurar que se ejecute después de que el DOM se actualice
            window.requestAnimationFrame(aplicarFormatoMoneda);
        }
    });

    // Observar cambios en todo el body
    observador.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class"] // Observar cambios en la clase
        // characterData: true // Descomentar si se necesita observar cambios de texto directo
    });
}

document.addEventListener("DOMContentLoaded", inicializarFormatoMonedaConObservador);

/**
 * Calcula totales en tablas con formato moneda
 * @param {string} tablaId - ID de la tabla
 * @param {Array} columnasNumero - Índices de columnas a sumar
 * @param {number} columnaTotalFila - Índice de columna para mostrar total por fila (opcional)
 * @param {string} selectorTotalGeneral - Selector CSS para el elemento del total general (ej. 'tfoot .total-general')
 * @returns {number} Total calculado
 */
function calcularTotalesTabla(tablaId, columnasNumero, columnaTotalFila, selectorTotalGeneral) {
    const tabla = document.getElementById(tablaId);
    if (!tabla) return 0;

    const filas = tabla.querySelectorAll("tbody tr");
    let totalGeneral = 0;

    filas.forEach(function(fila) {
        let subtotalFila = 0;

        columnasNumero.forEach(function(indiceColumna) {
            const celda = fila.cells[indiceColumna];
            if (celda) {
                const valor = celda.textContent || celda.innerText;
                subtotalFila += desformatearNumero(valor);
            }
        });

        if (columnaTotalFila !== undefined && fila.cells[columnaTotalFila]) {
            const celdaTotalFila = fila.cells[columnaTotalFila];
            const decimales = celdaTotalFila.dataset.decimales ? parseInt(celdaTotalFila.dataset.decimales) : 0;
            celdaTotalFila.textContent = formatearNumero(subtotalFila, decimales);
            celdaTotalFila.classList.add("formato-moneda");
        }

        totalGeneral += subtotalFila;
    });

    if (selectorTotalGeneral) {
        const elementoTotalGeneral = tabla.querySelector(selectorTotalGeneral);
        if (elementoTotalGeneral) {
            const decimales = elementoTotalGeneral.dataset.decimales ? parseInt(elementoTotalGeneral.dataset.decimales) : 0;
            elementoTotalGeneral.textContent = formatearNumero(totalGeneral, decimales);
            elementoTotalGeneral.classList.add("formato-moneda");
        }
    }

    return totalGeneral;
}

