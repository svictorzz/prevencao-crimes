from flask import Flask, render_template, request
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)

# Conexão com o MongoDB
client = MongoClient("mongodb+srv://scrumTeam:OsRV9Q3IUvdoGOZt@clusteres3.lj0e2.mongodb.net/?retryWrites=true&w=majority&appName=clusterES3")
db = client["crime_db"]
crimes_collection = db["crimes"]

@app.route("/", methods=["GET", "POST"])
def index():
    # Buscar as regiões distintas diretamente no banco de dados
    regions = list(crimes_collection.distinct("area"))

    # Se não houver regiões cadastradas, exibir uma mensagem
    if not regions:
        regions = ["Nenhuma região disponível"]

    # Buscar as coordenadas e o tipo de crime para exibir no mapa
    crimes = list(crimes_collection.find().limit(50))  # Exemplo de limite para exibir apenas os 10 primeiros

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

    # Formatar a data de cada crime para um formato amigável
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

if __name__ == "__main__":
    app.run(debug=True)
