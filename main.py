from flask import Flask, request, jsonify, abort
from flask_restful import Api, Resource, reqparse, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
import lotterySIM
from lotteries import LOTTERIES
from copy import deepcopy


PORT = 5000
HOST = "127.0.0.1"

app = Flask(__name__)
api = Api(app)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)

class SimulationModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    simulation = db.Column(db.PickleType, nullable=False)
    
    def __repr__(self):
        return f"Simulation({self.id}, {self.simulation.get_results()})"

db.drop_all()
db.create_all()


simulation_create_args = reqparse.RequestParser()
simulation_create_args.add_argument("lottery_name", type=str, help="Name of the lottery", required=True)
simulation_create_args.add_argument("guess", type=int, action="append", help="Player's guess", required=False)

simulation_get_args = reqparse.RequestParser()
simulation_get_args.add_argument("speed", type=int, help="Number of year's passed every request", required=False)



class Lottery(Resource):
    def patch(self, id):
        args = simulation_get_args.parse_args()
        simulation_model = SimulationModel.query.get_or_404(id)
            
        speed = args.get("speed")
        # 200 years per request limit
        speed = min(speed, 200) if speed is not None else 1 

        simulation = deepcopy(simulation_model.simulation)
        
        simulation.simulate_years(speed)
        result_data = simulation.get_results()
        
        simulation_model.simulation = simulation 
        
        db.session.add(simulation_model)
        db.session.commit()
        
        return jsonify(result_data)

    
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
        
        if SimulationModel.query.get(id) is None:
            simulation_model = SimulationModel(id=id, simulation=simulation)
            db.session.add(simulation_model)
            db.session.commit()
        else:
            abort(400, "ID already exists") 
        
        return {"lottery": lottery_name, "simulation_id": id, "guess": player.get_guess()}, 201
    
    
    def delete(self, id):
        SimulationModel.query.filter_by(id=id).delete()
        db.session.commit()
        
    
api.add_resource(Lottery, "/lottery/<int:id>")


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
    # pip install -r requirements.txt