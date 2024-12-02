from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from twilio.rest import Client

app = Flask(__name__)

# Conexão com o MongoDB
client = MongoClient("mongodb+srv://scrumTeam:OsRV9Q3IUvdoGOZt@clusteres3.lj0e2.mongodb.net/?retryWrites=true&w=majority&appName=clusterES3")
db = client["crime_db"]
crimes_collection = db["crimes"]

# Configuração do Twilio
twilio_sid = 'AC18d8aed0340bcc295a0a6191258bb982'
twilio_auth_token = 'a18c34062e00275b64b3a74318219bc6'
twilio_phone_number = '5511976620206'
twilio_client = Client(twilio_sid, twilio_auth_token)

def send_sms_notification(crime):
    """Função para enviar SMS notificando sobre um novo crime"""
    try:
        message = twilio_client.messages.create(
            body=f"Novo Crime Reportado!\nTipo: {crime['crime_type']}\nLocalização: {crime['area']}\nHora: {crime['formatted_time']}\nDescrição: {crime['description']}",
            from_=twilio_phone_number,
            to='+553186113922'
        )
        print(f"SMS enviado com sucesso! SID: {message.sid}")
    except Exception as e:
        print(f"Erro ao enviar SMS: {str(e)}")

@app.route("/", methods=["GET", "POST"])
def index():
    # Buscar as regiões distintas diretamente no banco de dados
    regions = list(crimes_collection.distinct("area"))

    # Se não houver regiões cadastradas, exibir uma mensagem
    if not regions:
        regions = ["Nenhuma região disponível"]

    # Buscar as coordenadas e o tipo de crime para exibir no mapa
    crimes = list(crimes_collection.find().limit(100)) 

    # Alterando a criação de crime_locations para incluir o crime_id
    crime_locations = [
    {"lat": crime.get("latitude"), "lng": crime.get("longitude"), "type": crime.get("crime_type"), "id": str(crime.get("_id"))}
    for crime in crimes if crime.get("latitude") and crime.get("longitude") and crime.get("crime_type")
    ]

    return render_template("index.html", regions=regions, crime_locations=crime_locations)


@app.route("/search", methods=["GET", "POST"])
def search():
    crime_type = request.args.get("crime_type", "").strip()
    region = request.args.get("region", "").strip()

    # Montar a consulta para MongoDB
    query = {}
    if crime_type:
        query["crime_type"] = {"$regex": f"^{crime_type}$", "$options": "i"}
    
    if region and region != "Nenhuma região disponível":
        query["area"] = {"$regex": f"^{region}$", "$options": "i"}

    # Consultando crimes no MongoDB, ordenando por tipo
    crimes = list(crimes_collection.find(query).sort([("crime_type", 1)]))

    # Contagem de crimes por região
    crime_counts_by_region = list(crimes_collection.aggregate([
        {"$match": query},
        {"$group": {"_id": "$area", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}  # Ordenar por maior incidência
    ]))

    # Formatar a data de cada crime
    for crime in crimes:
        crime_time = crime.get("time")  
        if crime_time:
            crime_datetime = datetime.fromisoformat(crime_time.replace("Z", "+00:00"))
            crime["formatted_time"] = crime_datetime.strftime("%d de %B de %Y, %H:%M")

    # Passar a variável 'regions' para o template
    regions = list(crimes_collection.distinct("area"))
    if not regions:
        regions = ["Nenhuma região disponível"]        

    return render_template("search.html", crimes=crimes, crime_type=crime_type, region=region, crime_counts_by_region=crime_counts_by_region, regions=regions)


@app.route("/crime/<crime_id>")
def crime_detail(crime_id):
    try:
        # Converte o crime_id para o tipo ObjectId
        crime = crimes_collection.find_one({"_id": ObjectId(crime_id)})

        # Verificar se o crime existe
        if not crime:
            return "Crime não encontrado", 404

        # Formatar a data do crime
        crime_time = crime.get("time")
        if crime_time:
            crime_datetime = datetime.fromisoformat(crime_time.replace("Z", "+00:00"))
            crime["formatted_time"] = crime_datetime.strftime("%d de %B de %Y, %H:%M")
        
        return render_template("crime_detail.html", crime=crime)
    except Exception as e:
        # Se ocorrer um erro na conversão ou na busca, exibe uma mensagem genérica
        return f"Erro ao procurar o crime: {str(e)}", 500


@app.route("/add_crime", methods=["GET", "POST"])
def add_crime():
    if request.method == "POST":
        # Capturar dados do formulário
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        crime_type = request.form.get("crime_type")
        area = request.form.get("area")
        time = request.form.get("time")
        description = request.form.get("description")

        # Validar campos obrigatórios
        if not (latitude and longitude and crime_type and area and time and description):
            return redirect(url_for('add_crime', message="Todos os campos são obrigatórios!", status="error"))

        # Inserir no banco de dados
        crime = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "crime_type": crime_type,
            "area": area,
            "time": time,
            "description" : description
        }
        crimes_collection.insert_one(crime)

        # Enviar notificação por SMS
        send_sms_notification(crime)

        return redirect(url_for('add_crime', message="Crime cadastrado com sucesso!", status="success"))

    # Exibir página de cadastro
    return render_template("add_crime.html")  

if __name__ == "__main__":
    app.run(debug=True)
