from flask import Flask, request, jsonify, abort
from flask_restful import Api, Resource, reqparse
from flask_sqlalchemy import SQLAlchemy
import lotterySIM
from lotteries import LOTTERIES


PORT = 5000
HOST = "127.0.0.1"

app = Flask(__name__)
api = Api(app)
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
# db = SQLAlchemy(app)


# class LotteryModel(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
    

# db.create_all()


# kolizje id
# nadaj id w zaleleznosci do klienta
# usun z listy gdy polaczenie zerwane


simulation_sessions = {}


simulation_create_args = reqparse.RequestParser()
simulation_create_args.add_argument("lottery_name", type=str, help="Name of the lottery", required=True)
simulation_create_args.add_argument("guess", type=int, action="append", help="Player's guess", required=False)

simulation_get_args = reqparse.RequestParser()
simulation_get_args.add_argument("speed", type=int, help="Number of year's passed every request", required=False)


class Lottery(Resource):
    def get(self, id):
        args = simulation_get_args.parse_args()
        sim_data = simulation_sessions.get(id)
        
        if sim_data is None:
            abort(404, "Simulation ID is not valid")
            
        speed = args.get("speed")
        # 200 years per request limit
        speed = min(speed, 200) if speed is not None else 1 

        simulation = sim_data["simulation"]
        
        simulation.simulate_years(speed)
        data = simulation.get_results()
        
        return jsonify(data)

    
    def put(self, id):
        args = simulation_create_args.parse_args()
             
        lottery_name = args.get("lottery_name")
        if lottery_name not in LOTTERIES:
            abort(400, "Lottery name is not valid")
            
        lottery = LOTTERIES[lottery_name] 
        
        player = lotterySIM.Player()
        
        guess = args.get("guess")
        if guess is None:
            player.generate_guess(lottery)
        else:
            valid = player.set_guess(guess, lottery=lottery)        
            if not valid:
                abort(400, "Player's guess is not valid")            
            
        simulation = lotterySIM.Simulation(
            lottery, player, rounds_per_week=3
        )
        
        simulation_sessions[id] = {"simulation": simulation}
        return {"lottery": lottery_name, "simulation_id": id, "guess": player.get_guess()}, 201
    
    def delete(self, id):
        if id in simulation_sessions:
            del simulation_sessions[id]
        else:
            abort(400, "Simulation ID is not valid")
    
    
api.add_resource(Lottery, "/lottery/<string:id>")


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
    # pip install -r requirements.txt