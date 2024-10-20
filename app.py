from flask import Flask, request, jsonify, abort
from flask_restful import Api, Resource, reqparse, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import lotterySIM
from lotteries import LOTTERIES
from copy import deepcopy


app = Flask(__name__)
api = Api(app)
CORS(app)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)

class SimulationModel(db.Model):
    id = db.Column(db.String, primary_key=True)
    simulation = db.Column(db.PickleType, nullable=False)
    
    def __repr__(self):
        return f"Simulation({self.id}, {self.simulation.get_results()})"

db.drop_all()
db.create_all()
 

simulation_create_args = reqparse.RequestParser()
simulation_create_args.add_argument("lottery_name", type=str, help="Name of the lottery", required=False)
simulation_create_args.add_argument("guess", type=int, action="append", help="Player's guess", required=False)
simulation_create_args.add_argument("rounds_per_week", type=int, help="Number of simulated lotteries each week", required=False)

simulation_create_args.add_argument("custom", type=bool, help="Is lottery custom", required=False)
simulation_create_args.add_argument("custom_guess_table", type=list, action="append", help="Custom table of guesses", required=False)
simulation_create_args.add_argument("custom_reward_table", type=dict, help="Custom table of rewards", required=False)
simulation_create_args.add_argument("custom_guess_price", type=float, help="Custom price of each guess", required=False)

simulation_get_args = reqparse.RequestParser()
simulation_get_args.add_argument("speed", type=int, help="Number of year's passed every request", required=False)



class Lottery(Resource):
    def get(self, id):
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
        
        data = jsonify(result_data)
        data.headers.add('Access-Control-Allow-Origin', '*')
        
        return data 

    
    def post(self, id):
        args = simulation_create_args.parse_args()
             
        lottery_name = args.get("lottery_name")
        is_custom = bool(args.get("custom"))
        
        if is_custom:
            guess_table = args.get("custom_guess_table")
            reward_table = args.get("custom_reward_table")
            guess_price = args.get("custom_guess_price")
            
            if not (type(guess_table) == list 
                    and type(reward_table) == dict 
                    and (type(guess_price) == int or type(guess_price) == float)):
                abort(400, "Custom lottery arguments are invalid")
                
            lottery = lotterySIM.Lottery(
                rewards=reward_table,
                guess_price=guess_price,
                guess_table=guess_table
                )
            
            print(guess_price)
            print(guess_table)
            print(reward_table)
            
        elif lottery_name is None or lottery_name not in LOTTERIES:
            abort(400, "Lottery name is not valid")
            
        else:    
            lottery = LOTTERIES[lottery_name] 
        
        player = lotterySIM.Player()
        
        guess = args.get("guess")
        if guess is None:
            player.generate_guess(lottery)
        else:
            valid = player.set_guess(guess, lottery=lottery)        
            if not valid:
                abort(400, "Player's guess is not valid")            
            
        rounds_per_week = args.get("rounds_per_week")
        if rounds_per_week is None:
            rounds_per_week = 3 # DEFAULT rounds per week    
        
        simulation = lotterySIM.Simulation(
            lottery, player, rounds_per_week=rounds_per_week
        )

        # delete first
        SimulationModel.query.filter_by(id=id).delete()
        db.session.commit()
        
        simulation_model = SimulationModel(id=id, simulation=simulation)
        db.session.add(simulation_model)
        db.session.commit()
        
        data = jsonify({"lottery": lottery_name, "simulation_id": id, "guess": player.get_guess()})
        data.headers.add('Access-Control-Allow-Origin', '*')        
        
        return data
    
    
    def delete(self, id):
        SimulationModel.query.filter_by(id=id).delete()
        db.session.commit()
        
    
api.add_resource(Lottery, "/api/<string:id>")


if __name__ == "__main__":
    app.run(debug=True)
    # pip install -r requirements.txt