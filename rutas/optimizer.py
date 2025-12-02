import requests
import json
from django.conf import settings
import itertools

# --- PARTE 1: Obtener Distancias/Tiempos de Google Maps ---
def get_distance_matrix(points, origin_coords, api_key, dest_coords=None):
    """
    Obtiene la matriz de distancias entre:
    - origen
    - todos los puntos de entrega
    - (opcional) destino

    Índices en la matriz:
      0                 : origen
      1 .. num_points   : puntos de entrega
      num_points + 1    : destino (si dest_coords no es None)
    """
    all_points_coords = [f"{origin_coords['latitud']},{origin_coords['longitud']}"]

    # puntos de entrega
    for p in points:
        all_points_coords.append(f"{p.latitud},{p.longitud}")

    # punto destino opcional
    if dest_coords is not None:
        all_points_coords.append(f"{dest_coords['latitud']},{dest_coords['longitud']}")

    origins_str = "|".join(all_points_coords)
    destinations_str = origins_str

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origins_str,
        "destinations": destinations_str,
        "mode": "driving",
        "key": api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'OK':
            distance_matrix = []
            for row_data in data['rows']:
                row_distances = []
                for element in row_data['elements']:
                    if element['status'] == 'OK':
                        row_distances.append(element['distance']['value'] / 1000)  # a km
                    else:
                        row_distances.append(float('inf'))
                distance_matrix.append(row_distances)
            return distance_matrix
        else:
            print(f"Error en Distance Matrix API: {data['status']} - {data.get('error_message', '')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con la API de Google Maps: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar la respuesta JSON de la API: {e}")
        return None

# --- PARTE 2: Algoritmo de Optimización (TSP Solver) ---
def solve_tsp(distance_matrix, num_points_entrega, start_index=0, end_index=None):
    """
    Resuelve el TSP:

    - Si end_index es None: ciclo
        start -> puntos -> start
    - Si end_index NO es None: camino
        start -> puntos -> end_index

    'num_points_entrega' = cantidad de puntos reales (sin contar origen ni destino).
    """
    if not distance_matrix or num_points_entrega == 0:
        return [], 0.0

    delivery_indices = list(range(1, num_points_entrega + 1))

    min_distance = float('inf')
    best_route = []

    for permutation in itertools.permutations(delivery_indices):
        if end_index is None:
            current_route_indices = [start_index] + list(permutation) + [start_index]
        else:
            current_route_indices = [start_index] + list(permutation) + [end_index]

        current_distance = 0.0

        for i in range(len(current_route_indices) - 1):
            origin_idx = current_route_indices[i]
            dest_idx = current_route_indices[i + 1]
            segment_distance = distance_matrix[origin_idx][dest_idx]
            if segment_distance == float('inf'):
                current_distance = float('inf')
                break
            current_distance += segment_distance

        if current_distance < min_distance:
            min_distance = current_distance
            best_route = current_route_indices

    return best_route, min_distance

# --- PARTE 3: Cálculos de Consumo ---
AUTO_RENDIMIENTO_KM_POR_LITRO = 12  # valor por defecto

def calculate_fuel_cost(total_distance_km, rendimiento_km_por_litro=AUTO_RENDIMIENTO_KM_POR_LITRO):
    """
    Calcula los litros de combustible consumidos (no el costo en dinero),
    en función de la distancia total y el rendimiento (km/L).

    El costo en CLP se calcula en la vista multiplicando:
        litros_consumidos * precio_bencina_CLP_por_L
    """
    if total_distance_km == float('inf'):
        return float('inf')
    if rendimiento_km_por_litro <= 0:
        return float('inf')  # evita división por cero o negativos
    return total_distance_km / rendimiento_km_por_litro

def calculate_fuel_consumption(total_distance_km, rendimiento_km_por_litro=AUTO_RENDIMIENTO_KM_POR_LITRO):
    """
    Alias de calculate_fuel_cost para mantener compatibilidad de nombre
    si más adelante quieres usarlo con este nombre.
    """
    return calculate_fuel_cost(total_distance_km, rendimiento_km_por_litro)
