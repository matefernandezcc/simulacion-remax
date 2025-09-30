import random
import heapq
import pandas as pd
import math
from typing import List, Dict, Optional, Set

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
        self.total_visitas_recibidas = 0
        self.tiempo_creacion = 0

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
        
        # ✅ NUEVO: Rastreo de propiedades en verificación
        self.propiedades_en_verificacion: Set[int] = set()  # IDs de propiedades

class SimulacionInmobiliaria:
    def __init__(self, config: Dict):
        # Configuración de parámetros
        self.config = config
        self.num_agentes = config['num_agentes']
        self.num_propiedades_activas = config['num_propiedades_activas']
        self.max_renegociaciones = config['max_renegociaciones']
        
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
        
        # ✅ JORNADA LABORAL
        self.usar_jornada_laboral = config.get('usar_jornada_laboral', False)
        if self.usar_jornada_laboral:
            self.hora_inicio_jornada = config.get('hora_inicio_jornada', 9) * 60  # 9 AM en minutos
            self.hora_fin_jornada = config.get('hora_fin_jornada', 18) * 60  # 6 PM en minutos
        
        # ✅ NUEVO: Parámetros para distribución de tiempo entre visitas
        self.usar_distribucion = config.get('usar_distribucion_visitas', False)
        if self.usar_distribucion:
            # Parámetros de la distribución Triangular del notebook
            self.dist_c = config.get('dist_c', 0.11683330812731067)
            self.dist_loc = config.get('dist_loc', 169.04207586301385)
            self.dist_scale = config.get('dist_scale', 30433.163765426078)
            # Calcular límites
            self.dist_a = self.dist_loc
            self.dist_b = self.dist_loc + self.dist_scale
            self.dist_m = self.dist_loc + self.dist_c * self.dist_scale
            # Calcular media de la triangular como referencia
            self.tiempo_entre_visitas = (self.dist_a + self.dist_m + self.dist_b) / 3
        else:
            # Tiempo fijo (modelo simple)
            self.tiempo_entre_visitas = config['tiempo_entre_visitas']
        
        # ✅ OPTIMIZACIÓN 1: Usar diccionarios para búsquedas O(1)
        self.agentes = {i: Agente(i) for i in range(self.num_agentes)}
        self.agentes_disponibles: Set[int] = set(range(self.num_agentes))  # Índice de disponibles
        
        # ✅ OPTIMIZACIÓN 2: Diccionarios de propiedades por estado
        self.propiedades_activas: Dict[int, Propiedad] = {}
        self.propiedades_vendidas: Dict[int, Propiedad] = {}
        self.propiedades_expiradas: Dict[int, Propiedad] = {}
        
        # Crear propiedades activas al inicio
        for i in range(self.num_propiedades_activas):
            prop = Propiedad(i)
            prop.tiempo_creacion = 0
            self.propiedades_activas[i] = prop
        
        self.tiempo_actual = 0
        self.total_ventas = 0
        self.ventas_perdidas = 0
        self.visitas_perdidas = 0
        self.visitas_perdidas_fuera_horario = 0
        self.visitas_sin_venta = 0
        self.total_visitas_generadas = 0
        self.eventos = []
        self.ventas_ganadas_por_re_engagement = 0
        
        # ✅ NUEVO: Control de reposición de propiedades
        self.proximo_id_propiedad = self.num_propiedades_activas  # Siguiente ID disponible
        self.mantener_propiedades_constante = config.get('mantener_propiedades_constante', True)
        self.propiedades_creadas_nuevas = 0  # Contador de propiedades creadas durante la simulación
        
        self.max_propiedades_verificacion_por_agente = config.get('max_propiedades_verificacion_por_agente', 3)
        self.visitas_perdidas_por_limite_verificacion = 0
        
        # Métricas
        self.tiempos_venta = []
        self.utilizacion_agentes = [0] * self.num_agentes
        
        # ✅ OPTIMIZACIÓN 3: Logging configurable (solo eventos importantes)
        self.verbose_logging = config.get('verbose_logging', False)
        self.log_actividades = []
        self.log_eventos_criticos = []  # Solo ventas, errores, etc.
        
    def convertir_a_horas_minutos(self, minutos_totales: float) -> str:
        """Convierte minutos totales a formato HH:MM"""
        horas = int(minutos_totales // 60)
        minutos = int(minutos_totales % 60)
        return f"{horas:02d}:{minutos:02d}"
    
    def convertir_a_dias_horas(self, horas_totales: float) -> str:
        """Convierte horas totales a formato legible (años, días, horas)"""
        años = int(horas_totales // (365 * 24))
        resto_horas = horas_totales % (365 * 24)
        dias = int(resto_horas // 24)
        horas = int(resto_horas % 24)
        
        partes = []
        if años > 0:
            partes.append(f"{años} año{'s' if años != 1 else ''}")
        if dias > 0:
            partes.append(f"{dias} día{'s' if dias != 1 else ''}")
        if horas > 0:
            partes.append(f"{horas} hora{'s' if horas != 1 else ''}")
        
        return ", ".join(partes) if partes else "0 horas"
    
    def generar_tiempo_entre_visitas(self) -> float:
        """✅ NUEVO: Genera tiempo entre visitas según configuración"""
        if self.usar_distribucion:
            # Inverse sampling de distribución Triangular
            U = random.uniform(0, 1)
            
            if U <= self.dist_c:
                # Primera rama: [a, m]
                X = self.dist_a + math.sqrt(U * (self.dist_b - self.dist_a) * (self.dist_m - self.dist_a))
            else:
                # Segunda rama: [m, b]
                X = self.dist_b - math.sqrt((1 - U) * (self.dist_b - self.dist_a) * (self.dist_b - self.dist_m))
            
            return X
        else:
            # Tiempo fijo
            return self.tiempo_entre_visitas
    
    def esta_en_horario_laboral(self) -> bool:
        """✅ NUEVO: Verifica si el tiempo actual está dentro de la jornada laboral"""
        if not self.usar_jornada_laboral:
            return True  # Si no se usa jornada, siempre es horario laboral
        
        # Obtener minutos del día actual (0-1439)
        minutos_del_dia = self.tiempo_actual % 1440
        
        return self.hora_inicio_jornada <= minutos_del_dia < self.hora_fin_jornada
        
    def registrar_actividad(self, mensaje: str, critico: bool = False):
        """Registra actividades - solo verboso si está habilitado"""
        if critico or self.verbose_logging:
            tiempo_actual_str = self.convertir_a_horas_minutos(self.tiempo_actual)
            log_entry = f"{tiempo_actual_str} -> {mensaje}"
            if critico:
                self.log_eventos_criticos.append(log_entry)
            if self.verbose_logging:
                self.log_actividades.append(log_entry)

    def bloquear_agente(self, agente_id: int, propiedad_id: int, tipo_evento: str, duracion: float):
        """✅ OPTIMIZADO: Bloquea un agente y actualiza índice de disponibles"""
        agente = self.agentes[agente_id]
        if agente.disponible:
            agente.disponible = False
            agente.propiedad_asignada = propiedad_id
            agente.tiempo_inicio_bloqueo = self.tiempo_actual
            agente.contador_tareas += 1
            # Remover de índice de disponibles
            self.agentes_disponibles.discard(agente_id)

    def desbloquear_agente(self, agente_id: int, propiedad_id: int):
        """✅ OPTIMIZADO: Desbloquea un agente y actualiza índice"""
        agente = self.agentes[agente_id]
        if not agente.disponible and agente.tiempo_inicio_bloqueo is not None:
            duracion_bloqueo = self.tiempo_actual - agente.tiempo_inicio_bloqueo
            agente.tiempo_total_bloqueado += duracion_bloqueo
            agente.disponible = True
            agente.propiedad_asignada = None
            agente.tiempo_inicio_bloqueo = None
            agente.tiempo_ultima_actividad = self.tiempo_actual
            # Agregar a índice de disponibles
            self.agentes_disponibles.add(agente_id)

    def buscar_agente_equitativo(self) -> Optional[int]:
        """✅ OPTIMIZADO: Búsqueda O(k) donde k = agentes disponibles"""
        if not self.agentes_disponibles:
            return None
        
        # Buscar solo entre disponibles el que menos tareas hizo
        agente_id = min(
            self.agentes_disponibles, 
            key=lambda aid: self.agentes[aid].contador_tareas
        )
        return agente_id

    def simular_venta(self) -> bool:
        """Simula si una visita resulta en venta"""
        return random.random() < self.prob_venta

    def simular_arrepentimiento(self) -> bool:
        """Simula si un cliente se arrepiente después de la venta"""
        return random.random() < self.prob_arrepentimiento

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

    def crear_nueva_propiedad(self):
        """✅ NUEVO: Crea una nueva propiedad (reposición automática)"""
        nueva_propiedad = Propiedad(self.proximo_id_propiedad)
        nueva_propiedad.tiempo_creacion = self.tiempo_actual
        self.propiedades_activas[self.proximo_id_propiedad] = nueva_propiedad
        self.proximo_id_propiedad += 1
        self.propiedades_creadas_nuevas += 1
        self.registrar_actividad(
            f"✨ NUEVA PROPIEDAD {nueva_propiedad.id} publicada - Total activas: {len(self.propiedades_activas)}",
            critico=False
        )
        return nueva_propiedad
    
    def programar_proxima_visita(self):
        """✅ MEJORADO: Programa la próxima visita (fija o aleatoria)"""
        tiempo_hasta_proxima = self.generar_tiempo_entre_visitas()
        proxima_visita = self.tiempo_actual + tiempo_hasta_proxima
        heapq.heappush(self.eventos, (proxima_visita, 'visita', None))

    def procesar_visita(self, _):
        """✅ OPTIMIZADO: Procesa visita con búsquedas O(1)"""
        self.total_visitas_generadas += 1
        
        # ✅ VERIFICAR HORARIO LABORAL
        if not self.esta_en_horario_laboral():
            self.visitas_perdidas_fuera_horario += 1
            self.registrar_actividad(f"❌ VISITA FUERA DE HORARIO - Hora: {self.tiempo_actual % 1440:.0f} min del día")
            return
        
        # Verificar si hay propiedades activas
        if not self.propiedades_activas:
            self.visitas_perdidas += 1
            self.registrar_actividad("❌ VISITA PERDIDA - No hay propiedades activas", critico=True)
            return
        
        # ✅ Seleccionar propiedad aleatoria - O(1) con choice sobre keys
        propiedad_id = random.choice(list(self.propiedades_activas.keys()))
        propiedad = self.propiedades_activas[propiedad_id]
        propiedad.total_visitas_recibidas += 1
        
        # Buscar agente disponible
        agente_id = self.buscar_agente_equitativo()
        
        if agente_id is None:
            self.visitas_perdidas += 1
            self.registrar_actividad(f"❌ VISITA PERDIDA prop {propiedad_id} - No hay agentes")
            return

        # Bloquear agente SIEMPRE
        self.bloquear_agente(agente_id, propiedad.id, "VISITA", self.tiempo_atencion_visitas)
        propiedad.tiempo_ultima_visita_agente = self.tiempo_actual
        propiedad.agente_asignado = agente_id
        propiedad.etapa_actual = 'visita'

        self.registrar_actividad(f"Agente {agente_id} → VISITA prop {propiedad_id} (#{propiedad.total_visitas_recibidas})")

        # Programar fin de visita
        tiempo_fin_visita = self.tiempo_actual + self.tiempo_atencion_visitas
        heapq.heappush(self.eventos, (tiempo_fin_visita, 'fin_visita', propiedad_id, agente_id))

    def procesar_fin_visita(self, propiedad_id: int, agente_id: int):
        """✅ OPTIMIZADO: Búsqueda O(1) en diccionario"""
        
        # ✅ Búsqueda O(1) en lugar de O(n)
        propiedad = self.propiedades_activas.get(propiedad_id)
        agente = self.agentes[agente_id]
        
        if not propiedad:
            self.registrar_actividad(f"⚠️ Prop {propiedad_id} no encontrada", critico=True)
            self.desbloquear_agente(agente_id, propiedad_id)
            return
        
        # Decidir venta al final
        hay_venta = self.simular_venta()
        
        # ✅ NUEVO: Verificar si el agente puede tomar más propiedades en verificación
        if hay_venta and len(agente.propiedades_en_verificacion) >= self.max_propiedades_verificacion_por_agente:
            # Rechazar venta porque el agente ya tiene demasiadas en verificación
            hay_venta = False
            self.visitas_perdidas_por_limite_verificacion += 1
            self.registrar_actividad(
                f"❌ Venta RECHAZADA - Agente {agente_id} tiene {len(agente.propiedades_en_verificacion)} props en verificación (máx: {self.max_propiedades_verificacion_por_agente})",
                critico=False
            )
        
        if hay_venta:
            # HAY VENTA - Continuar con papeles
            propiedad.en_venta = True
            self.registrar_actividad(f"Agente {agente_id} COMPLETA visita prop {propiedad_id} - ✅ VENTA", critico=True)
            
            propiedad.etapa_actual = 'papeles'
            tiempo_gestion_papeles = self.tiempo_actual + self.tiempo_gestion_papeles
            heapq.heappush(self.eventos, (tiempo_gestion_papeles, 'fin_gestion_papeles', propiedad_id, agente_id))
            
        else:
            # NO HAY VENTA - Liberar agente
            self.visitas_sin_venta += 1
            self.desbloquear_agente(agente_id, propiedad_id)
            
            propiedad.etapa_actual = None
            propiedad.agente_asignado = None
            
            self.registrar_actividad(f"Agente {agente_id} COMPLETA visita prop {propiedad_id} - ❌ SIN VENTA")

    def procesar_fin_gestion_papeles(self, propiedad_id: int, agente_id: int):
        """✅ OPTIMIZADO: Búsqueda O(1)"""
        
        propiedad = self.propiedades_activas.get(propiedad_id)
        if not propiedad:
            self.desbloquear_agente(agente_id, propiedad_id)
            return

        self.registrar_actividad(f"Agente {agente_id} COMPLETA papeles prop {propiedad_id}")

        if self.simular_arrepentimiento():
            propiedad.arrepentimiento = True
            self.registrar_actividad(f"ARREPENTIMIENTO prop {propiedad_id}", critico=True)
            
            propiedad.etapa_actual = 'renegociacion'
            tiempo_renegociacion = self.tiempo_actual + self.tiempo_gestion_renegociacion
            heapq.heappush(self.eventos, (tiempo_renegociacion, 'renegociacion', propiedad_id, agente_id))
                
        else:
            # No hay arrepentimiento - verificación (NO BLOQUEANTE)
            self.registrar_actividad(f"Prop {propiedad_id} → VERIFICACIÓN")
            self.desbloquear_agente(agente_id, propiedad_id)
            
            # ✅ NUEVO: Agregar propiedad a la lista de verificación del agente
            agente = self.agentes[agente_id]
            agente.propiedades_en_verificacion.add(propiedad_id)
            
            tiempo_verificacion = self.tiempo_actual + self.tiempo_gestion_verificacion
            heapq.heappush(self.eventos, (tiempo_verificacion, 'fin_verificacion', propiedad_id, agente_id))

    def procesar_renegociacion(self, propiedad_id: int, agente_id: int):
        """✅ OPTIMIZADO: Búsqueda O(1)"""
        
        propiedad = self.propiedades_activas.get(propiedad_id)
        if not propiedad:
            self.desbloquear_agente(agente_id, propiedad_id)
            return

        self.registrar_actividad(f"Agente {agente_id} COMPLETA renegociación prop {propiedad_id}")

        if self.rutina_reengagement(propiedad):
            self.registrar_actividad(f"RENEGOCIACIÓN EXITOSA prop {propiedad_id}", critico=True)
            self.desbloquear_agente(agente_id, propiedad_id)
            
            # ✅ NUEVO: Agregar propiedad a la lista de verificación del agente
            agente = self.agentes[agente_id]
            agente.propiedades_en_verificacion.add(propiedad_id)
            
            self.ventas_ganadas_por_re_engagement += 1
            tiempo_verificacion = self.tiempo_actual + self.tiempo_gestion_verificacion
            heapq.heappush(self.eventos, (tiempo_verificacion, 'fin_verificacion', propiedad_id, agente_id))
            
        else:
            self.registrar_actividad(f"RENEGOCIACIÓN FALLIDA prop {propiedad_id}", critico=True)
            self.ventas_perdidas += 1
            self.desbloquear_agente(agente_id, propiedad_id)
            
            propiedad.arrepentimiento = False
            propiedad.en_venta = False
            propiedad.etapa_actual = None

    def procesar_fin_verificacion(self, propiedad_id: int, agente_id: int):
        """✅ OPTIMIZADO: Búsqueda O(1)"""
        
        propiedad = self.propiedades_activas.get(propiedad_id)
        if not propiedad:
            # ✅ NUEVO: Remover de verificación si la propiedad ya no existe
            agente = self.agentes[agente_id]
            agente.propiedades_en_verificacion.discard(propiedad_id)
            return

        self.registrar_actividad(f"VERIFICACIÓN COMPLETADA prop {propiedad_id}")
        propiedad.paso_verificacion = True

        agente = self.agentes[agente_id]
        
        # ✅ NUEVO: Remover de la lista de verificación (ahora pasa a escribanía)
        agente.propiedades_en_verificacion.discard(propiedad_id)
        
        if agente.disponible:
            self.bloquear_agente(agente_id, propiedad_id, "ESCRIBANIA", self.tiempo_gestion_escribania)
            propiedad.etapa_actual = 'escribania'
            
            tiempo_escribania = self.tiempo_actual + self.tiempo_gestion_escribania
            heapq.heappush(self.eventos, (tiempo_escribania, 'fin_escribania', propiedad_id, agente_id))
        else:
            # Esperar (pero ya la sacamos de verificación)
            heapq.heappush(self.eventos, (self.tiempo_actual + 5, 'fin_verificacion', propiedad_id, agente_id))

    def procesar_fin_escribania(self, propiedad_id: int, agente_id: int):
        """✅ OPTIMIZADO: Búsqueda y remoción O(1)"""
        
        propiedad = self.propiedades_activas.get(propiedad_id)
        if propiedad and propiedad.paso_verificacion:
            # VENTA CONCRETADA
            self.total_ventas += 1
            tiempo_total_venta = self.tiempo_actual - propiedad.tiempo_ultima_visita_agente
            self.tiempos_venta.append(tiempo_total_venta)
            
            self.registrar_actividad(
                f"🎉 VENTA prop {propiedad_id} por Agente {agente_id} - "
                f"Tiempo: {self.convertir_a_horas_minutos(tiempo_total_venta)} - "
                f"Visitas: {propiedad.total_visitas_recibidas}",
                critico=True
            )
            
            # ✅ Remoción O(1) de diccionario
            del self.propiedades_activas[propiedad_id]
            self.propiedades_vendidas[propiedad_id] = propiedad
            
            # ✅ NUEVO: Reposición automática de propiedades
            if self.mantener_propiedades_constante:
                self.crear_nueva_propiedad()
                self.registrar_actividad(
                    f"🔄 Propiedad {propiedad_id} vendida → Nueva propiedad creada - "
                    f"Total activas: {len(self.propiedades_activas)}",
                    critico=False
                )
            
            self.desbloquear_agente(agente_id, propiedad_id)
        else:
            self.desbloquear_agente(agente_id, propiedad_id)

    def ejecutar_simulacion(self, tiempo_total_simulacion: float):
        """Ejecuta la simulación por el tiempo especificado (en HORAS)"""
        tiempo_total_minutos = tiempo_total_simulacion * 60
        
        print("🚀 INICIANDO SIMULACIÓN OPTIMIZADA")
        print(f"⏰ Tiempo total: {tiempo_total_simulacion:.0f} horas ({self.convertir_a_dias_horas(tiempo_total_simulacion)})")
        print(f"👥 Agentes: {self.num_agentes}")
        if self.usar_jornada_laboral:
            print(f"⏱️  Jornada laboral: {self.hora_inicio_jornada//60}:00 - {self.hora_fin_jornada//60}:00")
        else:
            print(f"⏱️  Jornada: 24/7 (sin restricciones)")
        print(f"🏠 Propiedades activas inicial: {len(self.propiedades_activas)}")
        if self.mantener_propiedades_constante:
            print(f"🔄 Reposición automática: ✅ ACTIVADA (se mantiene constante en {self.num_propiedades_activas})")
        else:
            print(f"🔄 Reposición automática: ❌ DESACTIVADA (número decrece con ventas)")
        #print(f"🔒 Límite de props en verificación/agente: {self.max_propiedades_verificacion_por_agente}")
        if self.usar_distribucion:
            print(f"📅 Visitas: Distribución Triangular (media ~{(self.dist_a + self.dist_m + self.dist_b)/3:.1f} min)")
        else:
            print(f"📅 Visitas cada: {self.tiempo_entre_visitas} minutos (FIJO)")
        print(f"🎯 P(Venta|Visita): {self.prob_venta*100:.1f}%")
        print(f"📝 Logging: {'VERBOSE' if self.verbose_logging else 'SOLO EVENTOS CRÍTICOS'}")
        print("=" * 50)

        # Programar primera visita
        self.programar_proxima_visita()

        # Bucle principal de simulación
        eventos_procesados = 0
        while self.eventos and self.tiempo_actual <= tiempo_total_minutos:
            tiempo_evento, tipo_evento, *args = heapq.heappop(self.eventos)
            self.tiempo_actual = tiempo_evento
            eventos_procesados += 1
            
            # Progress bar cada 10,000 eventos
            if eventos_procesados % 10000 == 0:
                progreso = (self.tiempo_actual / tiempo_total_minutos) * 100
                print(f"⏳ Progreso: {progreso:.1f}% - Eventos: {eventos_procesados:,} - Ventas: {self.total_ventas}", end='\r')
            
            if tipo_evento == 'visita':
                self.procesar_visita(None)
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

        print()  # Nueva línea después del progress bar
        self.calcular_metricas()
        self.generar_reporte()

    def calcular_metricas(self):
        """Calcula las métricas finales"""
        for agente_id, agente in self.agentes.items():
            if agente.tiempo_inicio_bloqueo is not None:
                tiempo_extra = self.tiempo_actual - agente.tiempo_inicio_bloqueo
                agente.tiempo_total_bloqueado += tiempo_extra
                agente.disponible = True
                agente.tiempo_inicio_bloqueo = None

    def generar_reporte(self):
        """Genera un reporte completo"""
        tiempo_total_horas = self.tiempo_actual / 60
        tiempo_total_str = self.convertir_a_horas_minutos(self.tiempo_actual)
        tiempo_promedio = sum(self.tiempos_venta) / len(self.tiempos_venta) if self.tiempos_venta else 0
        tiempo_promedio_str = self.convertir_a_horas_minutos(tiempo_promedio)
        
        comision_minima = self.negociacion(self.max_renegociaciones)
        tasa_conversion_visitas = self.total_ventas / max(self.total_visitas_generadas, 1)
        
        print("\n" + "=" * 80)
        print("📊 REPORTE FINAL DE SIMULACIÓN")
        print("=" * 80)
        
        print(f"\n⏰ TIEMPO:")
        print(f"  Total simulado: {tiempo_total_str} ({tiempo_total_horas:.0f} horas = {self.convertir_a_dias_horas(tiempo_total_horas)})")
        
        print(f"\n🏠 PROPIEDADES:")
        print(f"  Activas al inicio: {self.num_propiedades_activas}")
        print(f"  Activas al final: {len(self.propiedades_activas)}")
        if self.mantener_propiedades_constante:
            print(f"  ✅ Reposición automática: ACTIVADA")
            print(f"  Nuevas propiedades creadas: {self.propiedades_creadas_nuevas:,}")
        print(f"  Vendidas: {len(self.propiedades_vendidas)}")
        if self.mantener_propiedades_constante:
            print(f"  Tasa de rotación: {len(self.propiedades_vendidas)/(self.num_propiedades_activas + self.propiedades_creadas_nuevas)*100:.1f}%")
        else:
            print(f"  Tasa de venta: {len(self.propiedades_vendidas)/self.num_propiedades_activas*100:.1f}%")
        
        print(f"\n👥 VISITAS:")
        print(f"  Total generadas: {self.total_visitas_generadas:,}")
        print(f"  Con venta concretada: {self.total_ventas:,}")
        print(f"  Con venta perdida: {self.ventas_perdidas:,}")
        print(f"  Sin venta: {self.visitas_sin_venta:,}")
        print(f"  Perdidas (sin agentes): {self.visitas_perdidas:,}")
        if self.visitas_perdidas_por_limite_verificacion > 0:
            print(f"  Perdidas (agente saturado de props en verificación): {self.visitas_perdidas_por_limite_verificacion:,}")
        #if self.usar_jornada_laboral:
             #print(f"  Perdidas (fuera de horario): {self.visitas_perdidas_fuera_horario:,}")
        
        print(f"\n📈 TASAS DE CONVERSIÓN:")
        print(f"  Visitas → Ventas: {tasa_conversion_visitas:.1%}")
        print(f"  P(Venta|Visita) esperada: {self.prob_venta:.1%}")
        print(f"  Diferencia: {(tasa_conversion_visitas - self.prob_venta)*100:+.2f}%")
        
        print(f"\n💰 VENTAS:")
        print(f"  Concretadas: {self.total_ventas:,}")
        print(f"  Ganadas por re-engagement: {self.ventas_ganadas_por_re_engagement}")
        print(f"  Tiempo promedio por venta: {tiempo_promedio_str}")
        
        print(f"\n👨‍💼 UTILIZACIÓN DE AGENTES:")
        
        # ✅ CORRECCIÓN: Calcular tiempo efectivo según jornada laboral
        if self.usar_jornada_laboral:
            # Solo contar horas de jornada laboral
            horas_por_dia = (self.hora_fin_jornada - self.hora_inicio_jornada) / 60
            tiempo_efectivo = (self.tiempo_actual / 1440) * horas_por_dia * 60  # en minutos
            nota_jornada = f" (jornada {self.hora_inicio_jornada//60}:00-{self.hora_fin_jornada//60}:00)"
        else:
            # Contar todas las horas (24/7)
            tiempo_efectivo = self.tiempo_actual
            nota_jornada = " (24/7)"
        
        print(f"  Base de cálculo: {self.convertir_a_horas_minutos(tiempo_efectivo)}{nota_jornada}")
        print()
        
        for agente_id, agente in self.agentes.items():
            utilizacion = agente.tiempo_total_bloqueado / max(tiempo_efectivo, 1)
            tiempo_bloqueo_str = self.convertir_a_horas_minutos(agente.tiempo_total_bloqueado)
            tareas = agente.contador_tareas
            
            # Marcar si está sobrecargado
            marcador = " ⚠️ SOBRECARGA" if utilizacion > 1.0 else ""
            print(f"  Agente {agente_id}: {utilizacion:.1%} ({tiempo_bloqueo_str}) - Tareas: {tareas:,}{marcador}")
        
        # ✅ RESUMEN DE UTILIZACIÓN
        utilizaciones = [agente.tiempo_total_bloqueado / max(tiempo_efectivo, 1) for agente in self.agentes.values()]
        util_promedio = sum(utilizaciones) / len(utilizaciones)
        util_min = min(utilizaciones)
        util_max = max(utilizaciones)
        agentes_sobrecargados = sum(1 for u in utilizaciones if u > 1.0)
        
        print(f"\n  📊 RESUMEN UTILIZACIÓN:")
        print(f"     Promedio: {util_promedio:.1%}")
        print(f"     Mínimo: {util_min:.1%}")
        print(f"     Máximo: {util_max:.1%}")
        if agentes_sobrecargados > 0:
            print(f"     ⚠️  Agentes sobrecargados (>100%): {agentes_sobrecargados}/{len(self.agentes)}")
        
        if self.propiedades_vendidas:
            visitas_por_prop = [p.total_visitas_recibidas for p in self.propiedades_vendidas.values()]
            print(f"\n📊 VISITAS POR PROPIEDAD VENDIDA:")
            print(f"  Promedio: {sum(visitas_por_prop)/len(visitas_por_prop):.1f} visitas")
            print(f"  Mínimo: {min(visitas_por_prop)} visitas")
            print(f"  Máximo: {max(visitas_por_prop)} visitas")
        
        print(f"\n📝 LOGGING:")
        print(f"  Eventos críticos registrados: {len(self.log_eventos_criticos):,}")
        if self.verbose_logging:
            print(f"  Total actividades: {len(self.log_actividades):,}")
        
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
    'num_agentes': 80, 
    'num_propiedades_activas': 9537,  # Ajustar según tu modelo
    'max_renegociaciones': 3,
        
    'probabilidad_venta': 0.07,
    'probabilidad_arrepentimiento': 0.2,
    'probabilidad_base_reengagement': 0.3,
    'penalizacion_reengagement': 0.1,
    
    'tiempo_primer_contacto': 80,
    'tiempo_atencion_visitas': 90,
    'tiempo_gestion_papeles': 120, 
    'tiempo_gestion_ofertas': 90,
    'tiempo_gestion_verificacion': 43200,  # 30 días
    'tiempo_gestion_escribania': 150,
    'tiempo_gestion_renegociacion': 50,
    
    # ✅ JORNADA LABORAL
    'usar_jornada_laboral': True,  # True = agentes solo trabajan en horario definido
    'hora_inicio_jornada': 9,  # 9 AM
    'hora_fin_jornada': 14,  # 6 PM (18:00)
    
    # ✅ TIEMPO ENTRE VISITAS: Elegir una opción
    # Opción A: Valor FIJO (modelo simple) - RECOMENDADO PARA EMPEZAR
    'usar_distribucion_visitas': True,
    'tiempo_entre_visitas': 22.31,  # Calculado: ~11,500 min/propiedad ÷ 21,000 props
    
    # Opción B: Distribución TRIANGULAR (del notebook)
    # ⚠️ IMPORTANTE: Estos valores son POR PROPIEDAD
    # Para usarlos en el SISTEMA, debes DIVIDIR por num_propiedades_activas
    # 'usar_distribucion_visitas': True,
     'dist_c': 0.11683330812731067,
     'dist_loc': 169.04207586301385 / 9537,  # ← DIVIDIR
     'dist_scale': 30433.163765426078 / 9537,  # ← DIVIDIR
    
    # Control de logging
    'verbose_logging': False,  # True = guarda todo, False = solo eventos críticos
    
    # ✅ REPOSICIÓN AUTOMÁTICA DE PROPIEDADES
    'mantener_propiedades_constante': True,  # True = crea nueva propiedad cuando se vende una
    
    # ✅ LÍMITE DE PROPIEDADES EN VERIFICACIÓN POR AGENTE
    'max_propiedades_verificacion_por_agente': 3,  # Máximo de propiedades que un agente puede tener en verificación simultánea
}

if __name__ == "__main__":
    print("\n🎯 SIMULACIÓN INMOBILIARIA RE/MAX - VERSIÓN OPTIMIZADA")
    print("="*80)
    print("✅ Optimizaciones:")
    print("   • Diccionarios para búsquedas O(1)")
    print("   • Índice de agentes disponibles")
    print("   • Logging configurable")
    print("   • Progress bar en tiempo real")
    print("="*80)
    print()
    
    simulacion = SimulacionInmobiliaria(config=CONFIGURACION)
    
    # ⏰ IMPORTANTE: El parámetro está en HORAS
    # Ejemplos:
    #   360 horas = 15 días
    #   720 horas = 30 días (1 mes)
    #   8760 horas = 365 días (1 año)
    #   21900 horas = 912.5 días (2.5 años)
    
    simulacion.ejecutar_simulacion(8760*30)  # 1 año (para testing más rápido)
