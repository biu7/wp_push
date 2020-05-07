from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werobot.contrib.flask import make_view

from app import robot

from config import QR_SCENE, QR_EXP, PUSH_TEMPLATE_ID
from redis_util import redis_client

app = Flask(__name__)
app.config.from_object("config")

db = SQLAlchemy(app)

app.add_url_rule(
    rule='/robot/',
    endpoint='werobot',
    view_func=make_view(robot),
    methods=['GET', 'POST']
)


@app.route('/push')
def push():
    args = request.args
    new_down = args.get("new_down")
    total_down = args.get("total_down")
    total = args.get("total")
    unique_id = args["unique_id"]

    from models import PushMap
    push_map = PushMap.query.filter(PushMap.unique_id == unique_id).first()
    if not push_map:
        return jsonify({
            "code": 404,
            "message": "未找到 unique_id 对应的绑定记录！"
        })

    robot.client.send_template_message(
        user_id=push_map.openid,
        template_id=PUSH_TEMPLATE_ID,
        data={
            "new_down": {
                "value": new_down,
            },
            "total_down": {
                "value": total_down,
            },
            "total": {
                "value": total,
            }
        }
    )
    return jsonify({
        "code": 200
    })


@app.route('/check_scan')
def check_scan():
    unique_id = request.args["unique_id"]
    open_id = redis_client.get_scened_flag(unique_id)
    if open_id:
        from models import PushMap
        PushMap.insert_or_update({
            "unique_id": unique_id,
            "openid": open_id,
        })
        return jsonify({
            "code": 200
        })
    return jsonify({
        "code": 404
    })


@app.route("/get_qr_code")
def get_qr_code():
    unique_id = request.args["unique_id"]
    qr_data = robot.client.create_qrcode(
        data={"expire_seconds": QR_EXP, "action_name": "QR_SCENE", "action_info": {"scene": {"scene_id": QR_SCENE}}}
    )
    ticket = qr_data["ticket"]
    redis_client.set_ticket_unique(ticket, unique_id, QR_EXP)
    return jsonify(qr_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12345, debug=True)