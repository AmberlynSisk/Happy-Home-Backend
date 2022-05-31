from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow 
from flask_cors import CORS 
from flask_bcrypt import Bcrypt, generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.sqlite")
CORS(app)

# CLASSES

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    img = db.Column(db.String, nullable=True)
    members = db.relationship('Member', backref='User', cascade='all, delete, delete-orphan')


    def __init__(self, username, password, email, img):
        self.username = username
        self.password = password
        self.email = email
        self.img = img


class Member(db.Model):
    member_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lists = db.relationship('List', backref='Member', cascade='all, delete, delete-orphan')


    def __init__(self, first_name, last_name, is_admin, user_id):
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = is_admin
        self.user_id = user_id


class List(db.Model):
    list_id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    list_type = db.Column(db.String, nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.member_id'), nullable=False)

    def __init__(self, text, is_completed, list_type, member_id):
        self.text = text
        self.is_completed = is_completed
        self.list_type = list_type
        self.member_id = member_id


# SCHEMAS

class ListSchema(ma.Schema):
    class Meta:
        fields = ('list_id', 'text', 'is_completed', 'list_type')

list_schema = ListSchema()
multiple_list_schema = ListSchema(many=True)


class MemberSchema(ma.Schema):
    class Meta:
        fields = ('member_id', 'first_name', 'last_name', 'is_admin', 'lists')
    lists = ma.Nested(multiple_list_schema)


member_schema = MemberSchema()
multiple_member_schema = MemberSchema(many=True)


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username', 'password', 'email', 'img', 'members')
    members = ma.Nested(multiple_member_schema)

user_schema = UserSchema()
multiple_user_schema = UserSchema(many=True)


# USER ROUTES

@app.route('/user/add', methods=['POST'])
def add_user():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be json')

    post_data = request.get_json()
    username = post_data.get('username')
    password = post_data.get('password')
    email = post_data.get('email')
    img = post_data.get('img')

    username_duplicate = db.session.query(User).filter(User.username == username).first()

    if username_duplicate is not None:
        return jsonify("Error: The username is already registered.")

    email_duplicate = db.session.query(User).filter(User.username == username).first()

    if email_duplicate is not None:
        return jsonify("Error: The email is already registered.")

    encrypted_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username, encrypted_password, email, img)

    db.session.add(new_user)
    db.session.commit()

    return jsonify(user_schema.dump(new_user))


@app.route('/user/verify', methods=['POST'])
def verify_user():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be json')

    post_data = request.get_json()
    username = post_data.get('username')
    password = post_data.get('password')

    user = db.session.query(User).filter(User.username == username).first()

    if user is None:
        return jsonify("User NOT verified")

    if bcrypt.check_password_hash(user.password, password) == False:
        return jsonify("User NOT verified")

    return jsonify(user_schema.dump(user))


@app.route('/user/get', methods=['GET'])
def get_all_users():
    all_users = db.session.query(User).all()
    return jsonify(multiple_user_schema.dump(all_users))


@app.route('/user/get/<id>', methods=["GET"])
def get_user_by_id(id):
    user = db.session.query(User).filter(User.id == id).first()
    return jsonify(user_schema.dump(user))


@app.route('/user/delete/<id>', methods=['DELETE'])
def delete_user_by_id(id):
    user = db.session.query(User).filter(User.id == id).first()
    db.session.delete(user)
    db.session.commit()

    return jsonify("The user has been deleted")


# MEMBER ROUTES

@app.route('/member/add', methods=["POST"])
def add_member():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be json')

    post_data = request.get_json()
    first_name = post_data.get('first_name')
    last_name = post_data.get('last_name')
    is_admin = post_data.get('is_admin')
    user_id = post_data.get('user_id')

    new_member = Member(first_name, last_name, is_admin, user_id)
    db.session.add(new_member)
    db.session.commit()

    return jsonify(member_schema.dump(new_member))


@app.route('/member/get/<id>', methods=["GET"])
def get_member_by_id(id):
    member = db.session.query(Member).filter(Member.member_id == id).first()
    return jsonify(member_schema.dump(member))


@app.route('/members/get/<user_id>', methods=["GET"])
def get_members_by_user_id(user_id):
    members = db.session.query(Member).filter(Member.user_id == user_id)
    return jsonify(multiple_member_schema.dump(members))


@app.route('/member/delete/<id>', methods=["DELETE"])
def delete_member_by_id(id):
    member = db.session.query(Member).filter(Member.id == id).first()
    db.session.delete(member)
    db.session.commit()
    
    return jsonify("The family member has been deleted.")


@app.route('/member/update/<id>', methods=["PUT", "PATCH"])
def update_member_by_id(id):
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be json')

    post_data = request.get_json()
    first_name = post_data.get('first_name')
    last_name = post_data.get('last_name')
    is_admin = post_data.get('is_admin')

    member = db.session.query(Member).filter(Member.id == id).first()

    if first_name != None:
        member.first_name = first_name
    if last_name != None:
        member.last_name = last_name
    if is_admin != None:
        member.is_admin = is_admin
    

    db.session.commit()
    return jsonify("Member has been updated")

# LIST ROUTES

@app.route('/item/add', methods=['POST'])
def add_item():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be json')

    post_data = request.get_json()
    text = post_data.get('text')
    is_completed = post_data.get('is_completed')
    list_type = post_data.get('list_type')
    member_id = post_data.get('member_id')

    new_item = List(text, is_completed, list_type, member_id)

    db.session.add(new_item)
    db.session.commit()

    return jsonify("Congrats, you've added an item to your list!")


@app.route('/item/update/<id>', methods=["PUT", "PATCH"])
def update_item_by_id(id):
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be json')

    post_data = request.get_json()
    text = post_data.get('text')
    is_completed = post_data.get('is_completed')
    list_type = post_data.get('list_type')
    member_id = post_data.get('member_id')

    item = db.session.query(List).filter(List.id == id).first()

    if text != None:
        item.text = text
    if is_completed != None:
        item.is_completed = is_completed
    if list_type != None:
        item.list_type = list_type
    if member_id != None:
        item.member_id = member_id
    

    db.session.commit()
    return jsonify("List item has been updated")


@app.route('/item/delete/<id>', methods=["DELETE"])
def delete_item_by_id(id):
    item = db.session.query(List).filter(List.id == id).first()
    db.session.delete(item)
    db.session.commit()
    
    return jsonify("The list item has been deleted.")



if __name__ == "__main__":
    app.run(debug=True)