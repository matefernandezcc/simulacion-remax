import csv

def limpiar_csv(archivo_entrada, archivo_salida):
    estados_validos = {"active", "completed", "canceled", "expired"}
    ultima_valida = None
    filas_validas = []

    with open(archivo_entrada, mode="r", encoding="utf-8-sig") as entrada:
        lector = csv.DictReader(entrada, delimiter=",")
        campos = [c for c in lector.fieldnames if c]  # limpia posibles None

        for fila in lector:
            if None in fila:
                fila.pop(None)  # elimina clave None si aparece

            estado = fila.get("estado", "").strip().lower()

            if estado in estados_validos:
                # guardar valor válido
                ultima_valida = estado
                filas_validas.append(fila)
            else:
                if ultima_valida:
                    # copiar estado de la fila anterior
                    fila["estado"] = ultima_valida
                    filas_validas.append(fila)
                # si no hay anterior, se descarta la fila

    with open(archivo_salida, mode="w", newline="", encoding="utf-8") as salida:
        escritor = csv.DictWriter(salida, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas_validas)

    print(f"Archivo limpio generado: {archivo_salida}")
    print(f"Filas finales: {len(filas_validas)}")

# Ejemplo de uso
limpiar_csv("propiedades_redremax.csv", "propiedades_limpio.csv")
