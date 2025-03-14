# Importamos Flask y requests
from flask import Flask, render_template, request, jsonify
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError


# Inicializamos la app Flask
app = Flask(__name__)
API_KEY = "6d2859045cd250ed3c8cf4245b951aae"


# Este es el codigo que hemos pasado desde el frontend en JS al backend en py
# Definimos la funcion de geolocalizacion pra obtener la latitud y la longuitud.
def get_coordinates(place: str, country: str = None) -> tuple[float, float] | None:
    """
    Obtiene las coordenadas (latitud, longitud) de un lugar utilizando geopy.

    Parámetros:
        place (str): Nombre del lugar (ciudad, dirección, etc.).
        country (str, opcional): Código de país (por ejemplo, "JP" para Japón).

    Retorna:
        tuple[float, float] | None: Una tupla con la latitud y longitud, o None si no se encuentra.
    """
    geolocator = Nominatim(
        user_agent="clima_app",
        timeout=10
    )

    try:
        # Construir la consulta
        query = place
        if country:
            query += f", {country}"

        # Obtener la ubicación
        location = geolocator.geocode(
            query,
            exactly_one=True,  # Forzar solo un resultado
            language='es'  # Idioma de los resultados
        )

        if location:
            return (location.latitude, location.longitude)
        else:
            print(f"No se pudo encontrar la ubicación para: {query}")
            return None

    except GeopyError as e:
        print(f"Error en geocodificación: {str(e)}")
        return None
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return None


# Función para hacer solicitudes HTTP
def make_request(url, params=None):
    """ Realiza una petición GET a una URL con parámetros opcionales y devuelve la respuesta JSON """
    try:
        response = requests.get(url, params=params, timeout=5)  # ⏳ Timeout para evitar bloqueos
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"error": "Ciudad no encontrada."}
    except requests.RequestException:
        return {"error": "No se pudo conectar al servicio."}
    return None  # Si hay otro error, devolvemos None



# Función para obtener la ubicación del usuario por IP
def get_user_location():
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)  # ⏳ Timeout agregado
        if response.status_code == 200:
            data = response.json()
            return data.get("city", "Madrid")  # Ciudad por defecto: Madrid
    except requests.RequestException:
        return "Madrid"  # En caso de error, devolver una ciudad válida




# Función para calcular la dirección del viento
def wind_direction(deg):
    directions = ["Norte", "Noreste", "Este", "Sureste", "Sur", "Suroeste", "Oeste", "Noroeste"]
    index = round(deg / 45) % 8
    return directions[index]




# Función para obtener el mensaje del clima
def get_weather_message(weather_description):
    if "cielo despejado" in weather_description:
        return "¡Es un día soleado, perfecto para entrenar todo el día!"
    elif any(term in weather_description for term in ["algo de nubes", "nubes dispersas", "muy nuboso", "nublado"]):
        return "¡El cielo está nublado, preparémonos para lo peor!"
    elif any(term in weather_description for term in ["lluvia ligera", "lluvia moderada", "lluvia intensa", "llovizna", "aguacero", "chubascos"]):
        return "¡La lluvia cae sin cesar, pero no hay obstáculo que no pueda superar!"
    elif any(term in weather_description for term in ["tormenta eléctrica", "tormenta con lluvia"]):
        return "¡Los truenos rugen en el cielo! ¡Este es el poder de la naturaleza desatada!"
    elif "nieve" in weather_description:
        return "¡Está nevando, derretiré la nieve con mi ardor guerrero!"
    else:
        return "El clima está tranquilo, puede que se avecine algo grande."
       


# Función para obtener el clima
def get_weather(city):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "es"
    }
    
    weather_data = make_request(base_url, params)

    if weather_data and "weather" in weather_data:
        if "wind" in weather_data and "deg" in weather_data["wind"]:
            weather_data["wind"]["direction"] = wind_direction(weather_data["wind"]["deg"])

        weather_data["message"] = get_weather_message(weather_data['weather'][0]['description'])
        return weather_data

    return {"error": "No se pudo obtener el clima"}



def show_weather(city):      #Funcion para procesar los datos en el backend y que solamente se muestren en el front. Si no, se procesarian en el front haciendo el codigo mas sucio y menos eficiente
    weather_data = get_weather(city)

    if "error" in weather_data:
       return {"error": weather_data["error"]}
    
    return {
        "city": weather_data["name"],
        "temperature": weather_data["main"]["temp"],
        "description": weather_data["weather"][0]["description"],
        "wind_speed": weather_data["wind"]["speed"],
        "wind_direction": weather_data["wind"]["direction"],
        "pressure": weather_data["main"]["pressure"],
        "icon": weather_data["weather"][0]["icon"],
        "message": weather_data["message"]
    }



# Ruta principal (Página de inicio)
@app.route("/", methods=["GET", "POST"])
def index():
    city = get_user_location()  # Ciudad por defecto basada en la IP
    if request.method == "POST":
        selected_city = request.form.get("city")
        custom_city = request.form.get("custom_city")
        city = custom_city if custom_city else selected_city

    weather_data = get_weather(city) if city else None
    return render_template("index.html", weather=weather_data)



# Ruta para obtener datos del clima desde el frontend
@app.route("/get_weather_data", methods=["POST"])
def get_weather_data():
    try:
        data = request.json  # 🚨 Puede fallar si el JSON no es válido
        city = data.get("city", get_user_location())  # Ciudad por defecto
        weather_data = get_weather(city) if city else None
        return jsonify(weather_data) if weather_data else jsonify({"error": "No se pudo obtener el clima"})
    except Exception:
        return jsonify({"error": "Error en la solicitud"}), 400



# Ruta para obtener la ciudad a partir de latitud y longitud
@app.route("/location", methods=["POST"])
def get_city_from_coords():
    try:
        data = request.json
        lat, lon = data.get("latitude"), data.get("longitude")

        if lat and lon:
            geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
            response = requests.get(geo_url, timeout=5)  # ⏳ Timeout agregado
            
            if response.status_code == 200 and response.json():
                city = response.json()[0].get("name", "Desconocido")
                return jsonify({"city": city})

        return jsonify({"error": "No se pudo obtener la ubicación"}), 400
    except Exception:
        return jsonify({"error": "Error en la solicitud"}), 400



# Iniciar la aplicación
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)