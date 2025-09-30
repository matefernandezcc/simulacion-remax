# 📅 GUÍA: Jornada Laboral en la Simulación

## ✅ ¿Qué se implementó?

Ahora puedes configurar que los agentes **NO trabajen 24/7**, sino solo en un horario específico.

---

## 🔧 CONFIGURACIÓN

### **Desactivado (por defecto):**
```python
CONFIGURACION = {
    'usar_jornada_laboral': False,  # Agentes trabajan 24/7
}
```

### **Activado:**
```python
CONFIGURACION = {
    'usar_jornada_laboral': True,
    'hora_inicio_jornada': 9,  # 9:00 AM
    'hora_fin_jornada': 18,    # 6:00 PM (18:00)
}
```

---

## ⚙️ ¿Cómo funciona?

### **1. Verificación de horario:**
Cada vez que llega una visita, el sistema verifica:
```python
minutos_del_dia = tiempo_actual % 1440  # 0-1439 (24 horas)

if hora_inicio <= minutos_del_dia < hora_fin:
    # ✅ Dentro de horario → procesar visita
else:
    # ❌ Fuera de horario → rechazar visita
```

### **2. Ejemplo práctico:**

**Configuración:**
- Horario: 9 AM - 6 PM (9 horas)
- Visitas cada: 10 minutos

**Resultado:**
- **Durante el día (9-18):** Se atienden visitas
- **Por la noche (18-9):** Visitas rechazadas

---

## 📊 IMPACTO EN LOS RESULTADOS

### **Sin jornada laboral (24/7):**
```
Horas disponibles: 24 horas/día
Capacidad: 144 visitas/día/agente (con 10 min/visita)
```

### **Con jornada laboral (9-18):**
```
Horas disponibles: 9 horas/día (37.5% del día)
Capacidad: 54 visitas/día/agente (con 10 min/visita)
Reducción: 62.5% ❌
```

---

## ⚠️ IMPORTANTE: Ajustar otros parámetros

Si activas la jornada laboral, **DEBES ajustar**:

### **Opción 1: Aumentar agentes**
```python
# SIN jornada: 10 agentes × 24h = 240 horas de capacidad
# CON jornada: 10 agentes × 9h = 90 horas de capacidad

# Necesitas 2.67x más agentes
'num_agentes': 27,  # En lugar de 10
```

### **Opción 2: Reducir visitas**
```python
# Si antes recibías visitas cada 1 minuto:
# Ahora necesitas recibirlas cada 2.67 minutos

'tiempo_entre_visitas': 2.67,  # En lugar de 1.0
```

### **Opción 3: Aumentar tiempo de atención**
Si las visitas solo llegan en horario laboral, esto ya reduce la carga.

---

## 🎯 EJEMPLO REALISTA

### **Sucursal RE/MAX (20-40 ventas/año):**

```python
CONFIGURACION = {
    'num_agentes': 3,
    'num_propiedades_activas': 500,
    
    # ✅ Jornada laboral de oficina
    'usar_jornada_laboral': True,
    'hora_inicio_jornada': 9,  # 9 AM
    'hora_fin_jornada': 18,    # 6 PM
    
    # Visitas solo en horario laboral
    'tiempo_entre_visitas': 60,  # 1 visita/hora
    'probabilidad_venta': 0.06,
}
```

**Resultado esperado:**
- **Visitas por día:** 9 horas × 1 visita/hora = 9 visitas/día
- **Visitas por año:** 9 × 365 = 3,285 visitas/año
- **Ventas esperadas:** 3,285 × 0.06 = ~197 ventas/año

Para llegar a 30 ventas/año:
```python
'tiempo_entre_visitas': 360,  # 1 visita cada 6 horas
# Resultado: ~1.5 visitas/día × 365 = 548 visitas/año × 0.06 = 33 ventas/año ✅
```

---

## 📈 REPORTE MODIFICADO

El reporte ahora muestra:

```
⏱️  Jornada laboral: 9:00 - 18:00

👥 VISITAS:
  Total generadas: 3,285
  Con venta concretada: 197
  Perdidas (fuera de horario): 15,320 ← NUEVO
```

---

## 🤔 ¿Cuándo usar jornada laboral?

### **✅ USA jornada laboral si:**
1. Quieres un modelo MÁS REALISTA
2. Tu sistema solo opera en horario de oficina
3. Quieres modelar limitaciones de recursos humanos

### **❌ NO uses jornada laboral si:**
1. Sistema opera 24/7 (ej: plataforma online)
2. Modelo simple para debugging
3. Quieres maximizar el throughput

---

## 💡 TIP: Combinar con distribución de visitas

Puedes hacer que las visitas lleguen aleatoriamente, pero solo se atiendan en horario:

```python
'usar_distribucion_visitas': True,  # Visitas aleatorias
'usar_jornada_laboral': True,       # Solo atendidas 9-18

# Resultado: Las visitas que caen fuera de 9-18 se pierden
```

Esto simula un comportamiento **muy realista** donde:
- Los clientes llaman/visitan a cualquier hora
- Pero solo son atendidos en horario de oficina
