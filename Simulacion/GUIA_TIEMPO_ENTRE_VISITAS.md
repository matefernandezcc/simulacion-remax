# 📊 GUÍA: Tiempo Entre Visitas - Fijo vs Aleatorio

## 🤔 ¿Cuál es la diferencia?

### **MODELO A: Tiempo FIJO** ⏱️ (actual por defecto)

```python
CONFIGURACION = {
    'usar_distribucion_visitas': False,
    'tiempo_entre_visitas': 40,  # SIEMPRE 40 minutos
}
```

**¿Qué hace?**
- Genera visitas cada **exactamente** 40 minutos
- Como un reloj: 0min, 40min, 80min, 120min, ...
- **Determinístico** (siempre igual)

**¿Cuándo usar?**
- Modelo simple y predecible
- Testing inicial
- Cuando el sistema recibe visitas muy regulares

---

### **MODELO B: Distribución TRIANGULAR** 🎲 (del notebook)

```python
CONFIGURACION = {
    'usar_distribucion_visitas': True,
    'dist_c': 0.11683330812731067,
    'dist_loc': 169.04207586301385,
    'dist_scale': 30433.163765426078,
}
```

**¿Qué hace?**
- Genera visitas con tiempos **aleatorios** siguiendo la distribución del notebook
- Tiempos varían: ~5 min, ~18 min, ~45 min, ~12 min, ...
- **Estocástico** (diferente cada vez)

**¿Cuándo usar?**
- Modelo realista basado en tus datos
- Para presentación final del trabajo
- Cuando quieres capturar la variabilidad real

---

## 🔢 ¿Qué representan los parámetros de la Triangular?

Tu distribución del notebook:

```
c     = 0.1168  → Posición de la moda (pico)
loc   = 169.04  → Mínimo (a)
scale = 30433.2 → Rango (b - a)

Valores calculados:
a (mín)  = 169.04 minutos  (~2.8 horas)
m (moda) = 3,724 minutos   (~62 horas = 2.6 días)  ← Valor más común
b (máx)  = 30,602 minutos  (~510 horas = 21 días)

Media ≈ 11,498 minutos (~191 horas = 8 días)
```

**Interpretación:**
- **Mínimo:** Una propiedad puede recibir visitas separadas por solo 3 horas
- **Máximo:** Puede pasar hasta 21 días sin visita
- **Más común:** ~2.6 días entre visitas

---

## ⚠️ PROBLEMA CONCEPTUAL EN TU MODELO ACTUAL

### **¿Qué calculaste en el notebook?**

**Tiempo entre visitas POR PROPIEDAD:**
```
Cada propiedad individual recibe visitas cada ~8 días (promedio)
```

### **¿Qué estás usando en la simulación?**

**Tiempo entre visitas AL SISTEMA COMPLETO:**
```
El sistema entero recibe una visita cada 40 minutos
```

---

## 🚨 ESTOS SON CONCEPTOS DIFERENTES

Imagina un hospital con 100 camas:

### **Por cama individual:**
- Cada cama recibe un paciente nuevo cada 7 días (promedio)
- Esto es lo que calculaste en el notebook ✅

### **Por hospital completo:**
- El hospital recibe pacientes cada: 7 días / 100 camas = ~1.7 horas
- Esto es lo que estás usando en la simulación ✅

---

## 💡 ¿CÓMO CONVERTIR ENTRE AMBOS?

Si tienes:
- **Tiempo por propiedad:** 8 días (11,520 minutos)
- **Propiedades activas:** 1,537

Entonces:
- **Tiempo al sistema:** 11,520 / 1,537 = **7.5 minutos** entre visitas

---

## 🎯 ¿QUÉ DEBERÍAS HACER?

### **Opción 1: Modelo SIMPLE (recomendado para inicio)**

```python
CONFIGURACION = {
    'usar_distribucion_visitas': False,
    'tiempo_entre_visitas': 7.5,  # Calculado: tiempo_prop / num_props
    'num_propiedades_activas': 1537,
}
```

**Resultado:**
- Sistema recibe visitas cada 7.5 minutos (FIJO)
- Fácil de predecir y verificar
- Bueno para debugging

---

### **Opción 2: Modelo REALISTA (para presentación final)**

```python
CONFIGURACION = {
    'usar_distribucion_visitas': True,
    'dist_c': 0.11683330812731067,
    'dist_loc': 169.04207586301385 / 1537,  # ← DIVIDIR por propiedades activas
    'dist_scale': 30433.163765426078 / 1537,
    'num_propiedades_activas': 1537,
}
```

**Resultado:**
- Sistema recibe visitas con tiempos ALEATORIOS
- Sigue la distribución real de tus datos
- Más realista pero más complejo

---

## 📊 COMPARACIÓN DE RESULTADOS

### Con **40 minutos FIJO:**
```
Visitas por día: 1,440 / 40 = 36 visitas/día
Visitas por año: 36 × 365 = 13,140 visitas/año

Si P(Venta) = 6%:
Ventas esperadas: 13,140 × 0.06 = 788 ventas/año
```

### Con **7.5 minutos FIJO:**
```
Visitas por día: 1,440 / 7.5 = 192 visitas/día
Visitas por año: 192 × 365 = 70,080 visitas/año

Si P(Venta) = 6%:
Ventas esperadas: 70,080 × 0.06 = 4,205 ventas/año 🚨 MUY ALTO
```

---

## 🎓 PARA TU TRABAJO (20-40 ventas/año)

Si quieres **30 ventas/año** con el dataset actual:

### **Cálculo inverso:**
```
Ventas deseadas: 30 por año
P(Venta): 6%

Visitas necesarias: 30 / 0.06 = 500 visitas/año
Visitas por día: 500 / 365 = 1.37 visitas/día

Tiempo entre visitas AL SISTEMA: 1,440 / 1.37 = 1,051 minutos ≈ 17.5 horas
```

### **Configuración sugerida:**
```python
CONFIGURACION = {
    'usar_distribucion_visitas': False,
    'tiempo_entre_visitas': 1051,  # ~17.5 horas
    'num_propiedades_activas': 200,  # Sucursal pequeña
    'num_agentes': 2,
    'probabilidad_venta': 0.06,
}
```

---

## ✅ RESUMEN

1. **El parámetro en `ejecutar_simulacion()` está en HORAS**
   ```python
   simulacion.ejecutar_simulacion(360)  # 15 días
   ```

2. **Tu distribución del notebook es POR PROPIEDAD, no por sistema**

3. **Tienes dos opciones:**
   - Tiempo FIJO: Simple, predecible
   - Tiempo ALEATORIO: Realista, basado en datos

4. **Para usar la distribución del notebook correctamente:**
   - Divide los parámetros por `num_propiedades_activas`
   - O úsala para modelar visitas a propiedades individuales (modelo diferente)

5. **Para 20-40 ventas/año:**
   - Ajusta `tiempo_entre_visitas` a ~1000 minutos
   - O reduce `probabilidad_venta` a ~0.2%
   - O reduce `num_propiedades_activas` a ~200
