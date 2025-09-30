import random
import heapq
import pandas as pd
from typing import List, Dict, Optional

class Propiedad:
    def __init__(self, id_propiedad):
        self.id = id_propiedad
        self.tiempo_comprometido_agente = 0
        self.tiempo_ultima_visita_agente = 0
        self.flag_escribania = False
        self.flag_verificacion = False
        self.contador_dias_verificacion = 0
        self.arrepentimiento = False
        self.contador_renegociaciones = 0
        self.en_venta = False
        self.historial_estados = []
        self.agente_asignado = None
        self.paso_verificacion = False
        self.etapa_actual = None
        self.total_visitas_recibidas = 0  # NUEVO: contar visitas por propiedad
        self.tiempo_creacion = 0  # NUEVO: cuándo se creó/publicó

class Agente:
    def __init__(self, id_agente):
        self.id = id_agente
        self.disponible = True
        self.tiempo_comprometido_propiedad = {}
        self.tiempo_proxima_visita = 0
        self.propiedad_asignada = None
        self.historial_bloqueos = []
        self.tiempo_total_bloqueado = 0
        self.tiempo_inicio_bloqueo = None
        self.tiempo_ultima_actividad = 0
        self.contador_tareas = 0

class SimulacionInmobiliaria:
    def __init__(self, config: Dict):
        # Configuración de parámetros
        self.config = config
        self.num_agentes = config['num_agentes']
        self.num_propiedades_activas = config['num_propiedades_activas']  # ✅ NUEVO
        self.max_renegociaciones = config['max_renegociaciones']
        self.tiempo_jornada_laboral = config['tiempo_jornada_laboral'] * 60
        
        # Probabilidades configurables
        self.prob_venta = config['probabilidad_venta']
        self.prob_arrepentimiento = config['probabilidad_arrepentimiento']
        self.prob_base_reengagement = config['probabilidad_base_reengagement']
        self.penalizacion_reengagement = config['penalizacion_reengagement']
        
        # Tiempos configurables (en minutos)
        self.tiempo_atencion_visitas = config['tiempo_atencion_visitas'] + config['tiempo_primer_contacto']
        self.tiempo_gestion_papeles = config['tiempo_gestion_papeles'] + config['tiempo_gestion_ofertas']
        self.tiempo_gestion_verificacion = config['tiempo_gestion_verificacion']
        self.tiempo_gestion_escribania = config['tiempo_gestion_escribania']
        self.tiempo_gestion_renegociacion = config['tiempo_gestion_renegociacion']
        self.tiempo_entre_visitas = config['tiempo_entre_visitas']
        
        # Estado de la simulación
        self.agentes = [Agente(i) for i in range(self.num_agentes)]
        
        # ✅ CAMBIO CRÍTICO: Crear propiedades activas AL INICIO
        self.propiedades_activas = [Propiedad(i) for i in range(self.num_propiedades_activas)]
        for prop in self.propiedades_activas:
            prop.tiempo_creacion = 0  # Todas empiezan al inicio
        
        self.propiedades_vendidas = []  # ✅ NUEVO: propiedades que se vendieron
        self.propiedades_expiradas = []  # ✅ NUEVO: propiedades que expiraron
        
        self.tiempo_actual = 0
        self.total_ventas = 0
        self.ventas_perdidas = 0
        self.visitas_perdidas = 0
        self.visitas_sin_venta = 0
        self.total_visitas_generadas = 0  # ✅ NUEVO: contador de visitas totales
        self.eventos = []
        self.ventas_ganadas_por_re_engagement = 0
        
        # Métricas
        self.tiempos_venta = []
        self.utilizacion_agentes = [0] * self.num_agentes
        self.log_actividades = []
        
    def convertir_a_horas_minutos(self, minutos_totales: float) -> str:
        """Convierte minutos totales a formato HH:MM"""
        horas = int(minutos_totales // 60)
        minutos = int(minutos_totales % 60)
        return f"{horas:02d}:{minutos:02d}"
        
    def registrar_actividad(self, mensaje: str):
        """Registra actividades importantes"""
        tiempo_actual_str = self.convertir_a_horas_minutos(self.tiempo_actual)
        log_entry = f"{tiempo_actual_str} -> {mensaje}"
        self.log_actividades.append(log_entry)
        #print(log_entry)

    def bloquear_agente(self, agente: Agente, propiedad_id: int, tipo_evento: str, duracion: float):
        """Bloquea un agente por una tarea específica"""
        if agente.disponible:
            agente.disponible = False
            agente.propiedad_asignada = propiedad_id
            agente.tiempo_inicio_bloqueo = self.tiempo_actual
            agente.contador_tareas += 1

    def desbloquear_agente(self, agente: Agente, propiedad_id: int):
        """Desbloquea un agente después de completar una tarea"""
        if not agente.disponible and agente.tiempo_inicio_bloqueo is not None:
            duracion_bloqueo = self.tiempo_actual - agente.tiempo_inicio_bloqueo
            agente.tiempo_total_bloqueado += duracion_bloqueo
            agente.disponible = True
            agente.propiedad_asignada = None
            agente.tiempo_inicio_bloqueo = None
            agente.tiempo_ultima_actividad = self.tiempo_actual

    def buscar_agente_equitativo(self) -> Optional[Agente]:
        """Busca el agente que ha hecho MENOS tareas para distribución equitativa"""
        agentes_disponibles = [a for a in self.agentes if a.disponible]
        if not agentes_disponibles:
            return None
        
        return min(agentes_disponibles, key=lambda x: x.contador_tareas)

    def simular_venta(self) -> bool:
        """Simula si una visita resulta en venta"""
        resultado = random.random() < self.prob_venta
        return resultado

    def simular_arrepentimiento(self) -> bool:
        """Simula si un cliente se arrepiente después de la venta"""
        resultado = random.random() < self.prob_arrepentimiento
        return resultado

    def rutina_reengagement(self, propiedad: Propiedad) -> bool:
        """Maneja la rutina de re-engagement para ventas caídas"""
        if propiedad.contador_renegociaciones >= self.max_renegociaciones:
            return False
        
        prob_convencimiento = max(0.1, self.prob_base_reengagement - 
                                (propiedad.contador_renegociaciones * self.penalizacion_reengagement))
        convencido = random.random() < prob_convencimiento
        
        if convencido:
            propiedad.contador_renegociaciones += 1
            propiedad.arrepentimiento = False
            return True
        return False

    def programar_proxima_visita(self):
        """Programa la próxima visita general - SOLO UNA cada X minutos"""
        proxima_visita = self.tiempo_actual + self.tiempo_entre_visitas
        heapq.heappush(self.eventos, (proxima_visita, 'visita', None))  # None porque no sabemos qué propiedad aún

    def procesar_visita(self, _):
        """
        Procesa una VISITA al sistema - se asigna a una propiedad EXISTENTE
        ✅ CORREGIDO: Agente SIEMPRE se bloquea durante la visita
        """
        self.total_visitas_generadas += 1
        
        # ✅ Verificar si hay propiedades activas disponibles
        if not self.propiedades_activas:
            self.visitas_perdidas += 1
            self.registrar_actividad(f"❌ VISITA PERDIDA - No hay propiedades activas en el sistema")
            return
        
        # ✅ Seleccionar una propiedad ALEATORIAMENTE del pool activo
        propiedad = random.choice(self.propiedades_activas)
        propiedad.total_visitas_recibidas += 1
        
        # Buscar agente disponible
        agente = self.buscar_agente_equitativo()
        
        if not agente:
            self.visitas_perdidas += 1
            self.registrar_actividad(f"❌ VISITA PERDIDA a propiedad {propiedad.id} - No hay agentes disponibles")
            return

        # ✅ BLOQUEAR AGENTE SIEMPRE (tenga venta o no)
        self.bloquear_agente(agente, propiedad.id, "VISITA", self.tiempo_atencion_visitas)
        propiedad.tiempo_ultima_visita_agente = self.tiempo_actual
        propiedad.agente_asignado = agente.id
        propiedad.etapa_actual = 'visita'

        self.registrar_actividad(f"Agente {agente.id} → VISITA propiedad {propiedad.id} (visita #{propiedad.total_visitas_recibidas})")

        # Programar FIN de visita (decidiremos venta al final)
        tiempo_fin_visita = self.tiempo_actual + self.tiempo_atencion_visitas
        heapq.heappush(self.eventos, (tiempo_fin_visita, 'fin_visita', propiedad.id, agente.id))

    def procesar_fin_visita(self, propiedad_id: int, agente_id: int):
        """
        Procesa el FIN de una visita - AQUÍ se decide si hubo venta
        ✅ CORREGIDO: Decisión de venta al FINAL de la visita
        """
        
        agente = self.agentes[agente_id]
        propiedad = next((p for p in self.propiedades_activas if p.id == propiedad_id), None)
        
        if not propiedad:
            self.registrar_actividad(f"⚠️ Propiedad {propiedad_id} no encontrada en activas")
            self.desbloquear_agente(agente, propiedad_id)
            return
        
        # ✅ DECIDIR VENTA AL FINAL de la visita
        hay_venta = self.simular_venta()
        
        if hay_venta:
            # ✅ HAY VENTA - Continuar con papeles (agente sigue bloqueado)
            propiedad.en_venta = True
            self.registrar_actividad(f"Agente {agente_id} COMPLETA visita propiedad {propiedad_id} - ✅ VENTA CONCRETADA")
            
            # EL MISMO AGENTE continúa con gestión de papeles
            propiedad.etapa_actual = 'papeles'
            
            tiempo_gestion_papeles = self.tiempo_actual + self.tiempo_gestion_papeles
            heapq.heappush(self.eventos, (tiempo_gestion_papeles, 'fin_gestion_papeles', propiedad_id, agente_id))
            
            self.registrar_actividad(f"Agente {agente_id} inicia GESTIÓN DE PAPELES propiedad {propiedad_id}")
        else:
            # ❌ NO HAY VENTA - Liberar agente
            self.visitas_sin_venta += 1
            self.desbloquear_agente(agente, propiedad_id)
            
            # Resetear estado de la propiedad
            propiedad.etapa_actual = None
            propiedad.agente_asignado = None
            
            self.registrar_actividad(f"Agente {agente_id} COMPLETA visita propiedad {propiedad_id} - ❌ SIN VENTA (liberado)")

    def procesar_fin_gestion_papeles(self, propiedad_id: int, agente_id: int):
        """Procesa el fin de la gestión de papeles"""
        
        propiedad = next((p for p in self.propiedades_activas if p.id == propiedad_id), None)
        agente = self.agentes[agente_id]

        if not propiedad:
            self.desbloquear_agente(agente, propiedad_id)
            return

        self.registrar_actividad(f"Agente {agente_id} COMPLETA gestión papeles propiedad {propiedad_id}")

        # Verificar arrepentimiento DESPUÉS de papeles
        if self.simular_arrepentimiento():
            propiedad.arrepentimiento = True
            self.registrar_actividad(f"CLIENTE propiedad {propiedad_id} se ARREPIENTE - iniciando renegociación")
            
            # EL MISMO AGENTE hace la renegociación
            propiedad.etapa_actual = 'renegociacion'
            
            tiempo_renegociacion = self.tiempo_actual + self.tiempo_gestion_renegociacion
            heapq.heappush(self.eventos, (tiempo_renegociacion, 'renegociacion', propiedad_id, agente_id))
            
            self.registrar_actividad(f"Agente {agente_id} inicia RENEGOCIACIÓN propiedad {propiedad_id}")
                
        else:
            # No hay arrepentimiento - iniciar verificación (NO BLOQUEANTE)
            self.registrar_actividad(f"Propiedad {propiedad_id} pasa a VERIFICACIÓN (no bloqueante)")
            
            # Liberar agente ya que la verificación no es bloqueante
            self.desbloquear_agente(agente, propiedad_id)
            
            # Programar fin de verificación
            tiempo_verificacion = self.tiempo_actual + self.tiempo_gestion_verificacion
            heapq.heappush(self.eventos, (tiempo_verificacion, 'fin_verificacion', propiedad_id, agente_id))

    def procesar_renegociacion(self, propiedad_id: int, agente_id: int):
        """Procesa la renegociación de una venta caída"""
        
        propiedad = next((p for p in self.propiedades_activas if p.id == propiedad_id), None)
        agente = self.agentes[agente_id]

        if not propiedad:
            self.desbloquear_agente(agente, propiedad_id)
            return

        self.registrar_actividad(f"Agente {agente_id} COMPLETA renegociación propiedad {propiedad_id}")

        if self.rutina_reengagement(propiedad):
            # Re-engagement exitoso - ahora debe pasar por VERIFICACIÓN
            self.registrar_actividad(f"RENEGOCIACIÓN EXITOSA propiedad {propiedad_id} - pasando a VERIFICACIÓN")
            
            # Liberar agente para verificación (no bloqueante)
            self.desbloquear_agente(agente, propiedad_id)
            
            self.ventas_ganadas_por_re_engagement += 1
            tiempo_verificacion = self.tiempo_actual + self.tiempo_gestion_verificacion
            heapq.heappush(self.eventos, (tiempo_verificacion, 'fin_verificacion', propiedad_id, agente_id))
            
        else:
            # Re-engagement fallido - ✅ Propiedad vuelve a estar disponible para más visitas
            self.registrar_actividad(f"RENEGOCIACIÓN FALLIDA propiedad {propiedad_id} - Propiedad vuelve al pool activo")
            self.ventas_perdidas += 1
            
            # Liberar agente
            self.desbloquear_agente(agente, propiedad_id)
            
            # ✅ La propiedad NO se remueve, sigue activa para recibir más visitas
            propiedad.arrepentimiento = False
            propiedad.en_venta = False
            propiedad.etapa_actual = None

    def procesar_fin_verificacion(self, propiedad_id: int, agente_id: int):
        """Procesa el fin del período de verificación"""
        
        propiedad = next((p for p in self.propiedades_activas if p.id == propiedad_id), None)
        agente = self.agentes[agente_id]
        
        if not propiedad:
            return

        self.registrar_actividad(f"VERIFICACIÓN COMPLETADA propiedad {propiedad_id} - iniciando escribanía")
        propiedad.paso_verificacion = True

        # EL MISMO AGENTE hace la escribanía
        if agente.disponible:
            self.bloquear_agente(agente, propiedad_id, "ESCRIBANIA", self.tiempo_gestion_escribania)
            propiedad.etapa_actual = 'escribania'
            
            tiempo_escribania = self.tiempo_actual + self.tiempo_gestion_escribania
            heapq.heappush(self.eventos, (tiempo_escribania, 'fin_escribania', propiedad_id, agente_id))
            self.registrar_actividad(f"Agente {agente_id} inicia ESCRIBANÍA propiedad {propiedad_id}")
        else:
            # Si el agente no está disponible, esperar
            self.registrar_actividad(f"ESCRIBANÍA PROP {propiedad_id} EN ESPERA - agente {agente_id} ocupado")
            heapq.heappush(self.eventos, (self.tiempo_actual + 5, 'fin_verificacion', propiedad_id, agente_id))

    def procesar_fin_escribania(self, propiedad_id: int, agente_id: int):
        """
        Procesa el fin del proceso de escribanía - VENTA CONCRETADA
        ✅ CORREGIDO: Remueve propiedad del pool activo
        """
        
        propiedad = next((p for p in self.propiedades_activas if p.id == propiedad_id), None)
        agente = self.agentes[agente_id]

        if propiedad and propiedad.paso_verificacion:
            # VENTA CONCRETADA
            self.total_ventas += 1
            tiempo_total_venta = self.tiempo_actual - propiedad.tiempo_ultima_visita_agente
            self.tiempos_venta.append(tiempo_total_venta)
            
            self.registrar_actividad(
                f"🎉 VENTA CONCRETADA propiedad {propiedad_id} por Agente {agente_id} - "
                f"Tiempo: {self.convertir_a_horas_minutos(tiempo_total_venta)} - "
                f"Total visitas recibidas: {propiedad.total_visitas_recibidas}"
            )
            
            # ✅ REMOVER propiedad del pool activo
            if propiedad in self.propiedades_activas:
                self.propiedades_activas.remove(propiedad)
                self.propiedades_vendidas.append(propiedad)
                self.registrar_actividad(f"Propiedad {propiedad_id} REMOVIDA del pool - Quedan {len(self.propiedades_activas)} activas")
            
            # Desbloquear agente
            self.desbloquear_agente(agente, propiedad_id)
        else:
            self.registrar_actividad(f"ERROR: Propiedad {propiedad_id} intentó escribanía sin verificación")
            self.desbloquear_agente(agente, propiedad_id)

    def ejecutar_simulacion(self, tiempo_total_simulacion: float):
        """Ejecuta la simulación por el tiempo especificado"""
        tiempo_total_minutos = tiempo_total_simulacion * 60
        
        print("🚀 INICIANDO SIMULACIÓN")
        print(f"⏰ Tiempo total: {self.convertir_a_horas_minutos(tiempo_total_minutos)}")
        print(f"👥 Agentes: {self.num_agentes}")
        print(f"🏠 Propiedades activas inicial: {len(self.propiedades_activas)}")
        print(f"📅 Visitas cada: {self.tiempo_entre_visitas} minutos")
        print(f"🎯 P(Venta|Visita): {self.prob_venta*100:.1f}%")
        print("=" * 50)

        # Programar primera visita
        self.programar_proxima_visita()

        # Bucle principal de simulación
        while self.eventos and self.tiempo_actual <= tiempo_total_minutos:
            tiempo_evento, tipo_evento, *args = heapq.heappop(self.eventos)
            self.tiempo_actual = tiempo_evento
            
            if tipo_evento == 'visita':
                self.procesar_visita(None)
                # Programar próxima visita SOLO si no hemos superado el tiempo
                if self.tiempo_actual + self.tiempo_entre_visitas <= tiempo_total_minutos:
                    self.programar_proxima_visita()
            
            elif tipo_evento == 'fin_visita':
                propiedad_id, agente_id = args
                self.procesar_fin_visita(propiedad_id, agente_id)
            
            elif tipo_evento == 'fin_gestion_papeles':
                propiedad_id, agente_id = args
                self.procesar_fin_gestion_papeles(propiedad_id, agente_id)
            
            elif tipo_evento == 'renegociacion':
                propiedad_id, agente_id = args
                self.procesar_renegociacion(propiedad_id, agente_id)
            
            elif tipo_evento == 'fin_verificacion':
                propiedad_id, agente_id = args
                self.procesar_fin_verificacion(propiedad_id, agente_id)
            
            elif tipo_evento == 'fin_escribania':
                propiedad_id, agente_id = args
                self.procesar_fin_escribania(propiedad_id, agente_id)

        self.calcular_metricas()
        self.generar_reporte()

    def calcular_metricas(self):
        """Calcula las métricas finales"""
        for agente in self.agentes:
            if agente.tiempo_inicio_bloqueo is not None:
                tiempo_extra = self.tiempo_actual - agente.tiempo_inicio_bloqueo
                agente.tiempo_total_bloqueado += tiempo_extra
                agente.disponible = True
                agente.tiempo_inicio_bloqueo = None

    def generar_reporte(self):
        """Genera un reporte completo"""
        tiempo_total_str = self.convertir_a_horas_minutos(self.tiempo_actual)
        tiempo_promedio = sum(self.tiempos_venta) / len(self.tiempos_venta) if self.tiempos_venta else 0
        tiempo_promedio_str = self.convertir_a_horas_minutos(tiempo_promedio)
        
        comision_minima = self.negociacion(self.max_renegociaciones)
        
        # TASA DE ÉXITO CORREGIDA
        tasa_conversion_visitas = self.total_ventas / max(self.total_visitas_generadas, 1)
        
        tiempo_sin_reengagement = getattr(self, "tiempo_sin_reengagement", 0)
        
        print("\n" + "=" * 80)
        print("📊 REPORTE FINAL DE SIMULACIÓN")
        print("=" * 80)
        
        print(f"\n⏰ TIEMPO:")
        print(f"  Total simulado: {tiempo_total_str}")
        
        print(f"\n🏠 PROPIEDADES:")
        print(f"  Activas al inicio: {self.num_propiedades_activas}")
        print(f"  Activas al final: {len(self.propiedades_activas)}")
        print(f"  Vendidas: {len(self.propiedades_vendidas)}")
        print(f"  Tasa de venta de propiedades: {len(self.propiedades_vendidas)/self.num_propiedades_activas*100:.1f}%")
        
        print(f"\n👥 VISITAS:")
        print(f"  Total generadas: {self.total_visitas_generadas}")
        print(f"  Con venta concretada: {self.total_ventas}")
        print(f"  Con venta perdida (arrepentimiento): {self.ventas_perdidas}")
        print(f"  Sin venta: {self.visitas_sin_venta}")
        print(f"  Perdidas (sin agentes): {self.visitas_perdidas}")
        
        print(f"\n📈 TASAS DE CONVERSIÓN:")
        print(f"  Visitas → Ventas: {tasa_conversion_visitas:.1%}")
        print(f"  P(Venta|Visita) esperada: {self.prob_venta:.1%}")
        print(f"  Diferencia: {(tasa_conversion_visitas - self.prob_venta)*100:+.2f}%")
        
        print(f"\n💰 VENTAS:")
        print(f"  Concretadas: {self.total_ventas}")
        print(f"  Ganadas por re-engagement: {self.ventas_ganadas_por_re_engagement}")
        print(f"  Tiempo promedio por venta: {tiempo_promedio_str}")
        print(f"  Comisión promedio estimada: 3.6%")
        print(f"  Comisión mínima con re-engagement: {comision_minima * 100:.2f}%")
        
        print(f"\n👨‍💼 UTILIZACIÓN DE AGENTES:")
        for i, agente in enumerate(self.agentes):
            utilizacion = agente.tiempo_total_bloqueado / max(self.tiempo_actual, 1)
            tiempo_bloqueo_str = self.convertir_a_horas_minutos(agente.tiempo_total_bloqueado)
            tareas = agente.contador_tareas
            print(f"  Agente {i}: {utilizacion:.1%} ({tiempo_bloqueo_str}) - Tareas: {tareas}")
        
        # ✅ NUEVO: Estadísticas de visitas por propiedad
        if self.propiedades_vendidas:
            visitas_por_prop_vendida = [p.total_visitas_recibidas for p in self.propiedades_vendidas]
            print(f"\n📊 VISITAS POR PROPIEDAD VENDIDA:")
            print(f"  Promedio: {sum(visitas_por_prop_vendida)/len(visitas_por_prop_vendida):.1f} visitas")
            print(f"  Mínimo: {min(visitas_por_prop_vendida)} visitas")
            print(f"  Máximo: {max(visitas_por_prop_vendida)} visitas")
        
        print("=" * 80)

    def negociacion(self, N, max_intentos=6, inicio=0.036, fin=0.026):
        """Calcula la comisión mínima según el número de intentos de re-negociación"""
        total_descuento = inicio - fin
        pesos = [i for i in range(1, max_intentos + 1)]
        suma_pesos = sum(pesos)
        reduccion = sum(pesos[:min(N, max_intentos)]) / suma_pesos * total_descuento
        return inicio - reduccion
    
# Configuración
CONFIGURACION = {
    'num_agentes': 60, 
    'num_propiedades_activas': 21000,  # ✅ NUEVO: Según cálculo del notebook
    'max_renegociaciones': 6,
    'tiempo_jornada_laboral': 4,
        
    'probabilidad_venta': 0.06,  # 6% por visita (según dataset)
    'probabilidad_arrepentimiento': 0.2,
    'probabilidad_base_reengagement': 0.3,
    'penalizacion_reengagement': 0.1,
    
    'tiempo_primer_contacto': 80,
    'tiempo_atencion_visitas': 90,
    'tiempo_gestion_papeles': 120, 
    'tiempo_gestion_ofertas': 90,
    'tiempo_gestion_verificacion': 43200,  # 30 días - No bloqueante
    'tiempo_gestion_escribania': 150,
    'tiempo_gestion_renegociacion': 50,
    'tiempo_entre_visitas': 1.5,  # TEI al sistema (ajustado según dataset)
}

tiempo_sin_reengagement = (
    CONFIGURACION['tiempo_atencion_visitas']
    + CONFIGURACION['tiempo_primer_contacto']
    + CONFIGURACION['tiempo_gestion_papeles']
    + CONFIGURACION['tiempo_gestion_ofertas']
    + CONFIGURACION['tiempo_gestion_verificacion']
    + CONFIGURACION['tiempo_gestion_escribania']
)

if __name__ == "__main__":
    print("\n🎯 SIMULACIÓN INMOBILIARIA RE/MAX - MODELO CORREGIDO")
    print("="*80)
    print("✅ Modelo: Visitas a propiedades EXISTENTES")
    print(f"✅ Propiedades activas iniciales: {CONFIGURACION['num_propiedades_activas']}")
    print(f"✅ TEI (Tiempo Entre Visitas al sistema): {CONFIGURACION['tiempo_entre_visitas']} min")
    print(f"✅ P(Venta|Visita): {CONFIGURACION['probabilidad_venta']*100}%")
    print("="*80)
    print()
    
    simulacion = SimulacionInmobiliaria(config=CONFIGURACION)
    simulacion.ejecutar_simulacion(6240) 
