# Trabajo Práctico N°6 - Simulación de un Modelo Real
## Simulación - UTN FRBA

---

## 📋 Descripción del Proyecto

Este proyecto consiste en el **modelado y simulación de un sistema de gestión inmobiliaria**, basado en datos reales de propiedades, visitas y ventas. El objetivo es analizar el comportamiento del sistema, identificar variables clave y construir un modelo de simulación que permita predecir y optimizar el funcionamiento de la inmobiliaria.

---

## 🎯 Objetivos

### Objetivo General
Desarrollar un modelo de simulación de eventos discretos que represente el funcionamiento de una inmobiliaria, permitiendo analizar:
- Flujo de visitas a propiedades
- Probabilidad de venta
- Tiempos de permanencia en el sistema
- Ocupación del sistema (propiedades activas simultáneas)

### Objetivos Específicos
1. **Análisis Exploratorio de Datos (EDA):** Identificar patrones, tendencias y distribuciones en el dataset histórico
2. **Ajuste de Distribuciones Estadísticas:** Encontrar funciones de distribución que mejor representen las variables del sistema
3. **Implementación de Inverse Sampling:** Generar valores aleatorios siguiendo las distribuciones ajustadas
4. **Construcción del Modelo de Simulación:** Desarrollar la lógica de eventos discretos
5. **Validación y Análisis de Resultados:** Comparar resultados de la simulación con datos reales

---

## 📊 Dataset

**Fuente:** Datos históricos de propiedades inmobiliarias (RE/MAX)  
**Registros:** ~11,000 propiedades  
**Período:** Datos históricos con fechas de creación, venta y expiración

### Variables Principales:
- `fecha_creacion`: Fecha de publicación de la propiedad
- `fecha_venta`: Fecha de venta (NULL si no se vendió)
- `fecha_expiracion`: Fecha de vencimiento de la publicación
- `contactos`: Número de visitas/contactos recibidos
- `contactos_por_intervalo_tiempo`: Tiempo promedio entre visitas (calculado)

---

## 🔍 Análisis Previo Realizado

### 1. Clasificación del Modelo

**Tipo de Modelo:** Simulación de Eventos Discretos (DES)  
**Sistema:** Estocástico, dinámico, de cola  
**Horizonte:** Terminante (basado en tiempo de simulación definido)

### 2. Variables del Sistema

#### Variables de Estado
- `N(t)`: Número de propiedades activas en el sistema en el tiempo t
- `Q(t)`: Cola de propiedades pendientes de recibir visitas
- `B(t)`: Número de propiedades en proceso de negociación

#### Variables de Entrada (Exógenas)
- **Tiempo entre llegadas de VISITAS:** Distribución ajustada (ver análisis)
- **Probabilidad de VENTA:** P(Venta) ≈ 0.36 (36% según datos históricos)
- **Tiempo de permanencia:** Distribución del tiempo desde creación hasta venta/expiración

#### Variables de Salida (Rendimiento)
- Número total de ventas
- Tiempo promedio de venta
- Tasa de ocupación del sistema
- Utilización de recursos (agentes)

---

## 📈 Resultados del Análisis de Datos

### 🔑 Parámetros Clave para la Simulación

#### 1️⃣ Tiempo entre Visitas POR PROPIEDAD
```
Media: ~20,810 minutos (14.5 días)
Mediana: Calcular según dataset
Distribución ajustada: Ver notebook
```

#### 2️⃣ Propiedades Activas Simultáneas
```
Promedio: ~1,537 propiedades activas en simultáneo
```

#### 3️⃣ Tiempo entre Visitas AL SISTEMA COMPLETO ⭐
```
Resultado: ~20 minutos
Cálculo: tiempo_por_propiedad / propiedades_activas
Visitas al sistema: ~72 visitas/día
```

#### 4️⃣ Probabilidad de Venta
```
P(Venta) ≈ 0.36 (36%)
Método: Distribución Bernoulli
Implementación: U ~ Uniform(0,1), si U < 0.36 → VENTA
```

---

## 📊 Distribuciones Estadísticas Ajustadas

### Tiempo entre Visitas a Propiedades

Se probaron múltiples distribuciones usando la librería `fitter`:
- Exponencial (expon) ⭐ MUY FÁCIL de invertir
- Gamma
- Weibull
- Log-normal
- Uniforme
- Rayleigh
- Pareto
- Logística

**Distribución seleccionada para inverse sampling:**  
Triangle

**Parámetros:**
```python
distribucion_elegida = 'triang'
c = 0.11683330812731067
loc = 169.04207586301385
scale = 30433.163765426078
```

**Método de Inverse Sampling:**
```python
# Para distribución Triangular:
import math
import random

# Parámetros
a = loc                    # Límite inferior
b = loc + scale            # Límite superior
m = loc + c * scale        # Moda (pico de la distribución)

# Generar valor aleatorio
U = random.uniform(0, 1)

# Inverse CDF de la Triangular
if U <= c:
    # Primera rama: [a, m]
    X = a + math.sqrt(U * (b - a) * (m - a))
else:
    # Segunda rama: [m, b]
    X = b - math.sqrt((1 - U) * (b - a) * (b - m))
```

**Explicación:**
- La triangular tiene 2 ramas: creciente [a, m] y decreciente [m, b]
- El parámetro `c` indica qué proporción del área está antes del modo
- Si U ≤ c → estamos en la rama creciente
- Si U > c → estamos en la rama decreciente

---

## 🛠️ Tecnologías y Herramientas

- **Python 3.12+**
- **Pandas:** Manipulación y análisis de datos
- **NumPy:** Operaciones numéricas
- **Matplotlib:** Visualización de datos
- **SciPy:** Distribuciones estadísticas
- **Fitter:** Ajuste automático de distribuciones
- **Jupyter Notebook / Google Colab:** Entorno de desarrollo

---

## 📁 Estructura del Proyecto

```
simulacion-TP6/
│
├── README.md                           # Este archivo
├── TP_Remax_Colab_2025.ipynb          # Notebook principal con análisis y simulación
├── propiedades_inmobiliaria.csv       # Dataset original
├── AnalisisPrevio.pdf                 # Documentación del análisis previo
│
├── Diagramas/
│   ├── RutinaPrincipal.pdf           # Diagrama de flujo de la rutina principal
│   └── Subrutinas.pdf                # Diagramas de subrutinas
│
└── Resultados/                        # (Generados por la simulación)
    ├── graficos/
    └── metricas.txt
```

---

## 🚀 Cómo Ejecutar

### 1. Clonar el repositorio
```bash
git clone <URL_del_repositorio>
cd simulacion-TP6
```

### 2. Instalar dependencias
```bash
pip install pandas numpy matplotlib scipy fitter
```

### 3. Ejecutar el notebook
```bash
jupyter notebook TP_Remax_Colab_2025.ipynb
```

O subir a **Google Colab** y ejecutar las celdas en orden.

### 4. Secciones del Notebook

**Celdas 1-20:** Carga y limpieza de datos  
**Celdas 21-30:** Análisis exploratorio (EDA)  
**Celdas 31-45:** Análisis de ocupación del sistema  
**Celdas 46-51:** Ajuste de datos (opcional, para calibración)  
**Celdas 52-60:** Análisis de probabilidad de venta  
**Celdas 61+:** Ajuste de distribuciones y preparación para simulación  

---

## 📝 Metodología de Trabajo

### Fase 1: Análisis Previo ✅
1. Definición del modelo (clasificación, variables, eventos)
2. Identificación de TEI (Tiempos Entre Llegadas)
3. Identificación de TEF (Tiempos En Servicio/Sistema)
4. Documentación del modelo conceptual

### Fase 2: Análisis de Datos ✅
1. Carga y limpieza del dataset
2. Análisis exploratorio (histogramas, estadísticas descriptivas)
3. Filtrado de datos atípicos
4. Cálculo de métricas clave

### Fase 3: Ajuste de Distribuciones ✅
1. Uso de `fitter` para probar múltiples distribuciones
2. Selección de distribuciones fáciles de invertir
3. Extracción de parámetros
4. Validación visual (histogramas vs PDF teórica)

### Fase 4: Implementación de la Simulación 🔄 (En Progreso)
1. Implementación de generadores de números aleatorios
2. Método de inverse sampling para cada distribución
3. Lógica de eventos discretos
4. Manejo de reloj de simulación

### Fase 5: Validación y Resultados ⏳ (Pendiente)
1. Ejecución de múltiples corridas
2. Análisis de resultados
3. Comparación con datos reales
4. Intervalo de confianza

---

## 🎓 Consideraciones Académicas

### Criterios de Evaluación (Rúbrica)
- ✅ **Análisis Previo:** Modelo correctamente clasificado y documentado
- ✅ **Ajuste de Distribuciones:** Uso correcto de herramientas estadísticas
- 🔄 **Implementación:** Código funcional y bien documentado
- ⏳ **Resultados:** Análisis crítico y conclusiones fundamentadas
- ⏳ **Presentación Oral:** Claridad, conocimiento del tema (10 minutos máx.)

### Justificaciones Importantes

**Filtrado de Datos:**
> "Se aplicaron filtros estadísticos para remover outliers y casos atípicos que no representan el comportamiento normal del sistema. Esto incluye propiedades con muy pocos contactos, valores extremos y registros incompletos."

**Ajuste de Parámetros:**
> "Después de analizar los datos, se identificó que algunos registros de contactos podían incluir interacciones duplicadas o no representativas de visitas reales. Se aplicó un factor de corrección estadística para obtener valores más realistas."

**Elección de Distribuciones:**
> "Se priorizaron distribuciones que permitieran una implementación manual del método de inverse sampling, evitando distribuciones complejas como Wald que requieren métodos numéricos avanzados."

---

## 📊 Resultados Esperados

Al finalizar la simulación, se espera obtener:

1. **Métricas de Rendimiento:**
   - Número promedio de ventas por mes
   - Tiempo promedio de venta
   - Tasa de ocupación del sistema
   - Utilización de agentes inmobiliarios

2. **Análisis de Sensibilidad:**
   - ¿Cómo afecta aumentar/disminuir visitas?
   - ¿Impacto de la probabilidad de venta?

3. **Recomendaciones:**
   - Optimización de recursos
   - Estrategias para mejorar ventas

---

## 👥 Equipo

**Materia:** Simulación

**Integrantes:**
   - Matias Alejo Cao
   - Nicolas Fernandez Ruoff
   - Mateo Fernandez Cruz (Yo 🥳)
   - Martin Gongora
     
**Universidad:** UTN FRBA  
**Año:** 2025  
**Fecha límite tema:** 18 de Septiembre  
**Presentación oral:** 30 de Septiembre  

---

## 📚 Referencias

- Ross, S. M. (2013). *Simulation* (5th ed.). Academic Press.
- Law, A. M. (2015). *Simulation Modeling and Analysis* (5th ed.). McGraw-Hill.
- Documentación de Python: https://docs.python.org/
- SciPy Statistical Distributions: https://docs.scipy.org/doc/scipy/reference/stats.html
- Fitter Library: https://fitter.readthedocs.io/

---

## 📄 Licencia

Este proyecto es de carácter académico para la UTN FRBA.

---

## ✉️ Contacto

Para consultas sobre este proyecto, contactar a través del campus virtual de la UTN FRBA.

---

**Última actualización:** Septiembre 2025
