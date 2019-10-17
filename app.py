"""RanchoStop is a site focusing on a modern rebranding of Tarantulas."""
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
from random import choice, randint
from functools import wraps
from bson import json_util
from bson.json_util import loads, dumps
import json
from lvl_calc import level_calc

host = os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017/RanchoStop')
client = MongoClient(host=f'{host}?retryWrites=false')
db = client.get_default_database()
users = db.users
ranchos = db.ranchos
listings = db.listings
comments = db.comments
hatcheries = db.hatcheries

app = Flask(__name__)
app.config['SECRET_KEY'] = 'THISISMYSECRETKEY'

# SESSION_TYPE = 'mongodb'
# app.config.from_object(__name__)
# Session(app)


def login_required(f):
    """
    Require login to access a page.

    Adapted from:
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------HOME---------------------------
@app.route('/')
def home():
    """Return homepage."""
    current_user = None
    if 'user' in session:
        current_user = session['user']

        # print(current_user)
    return render_template('home.html', current_user=current_user)


@app.route('/home')
def home_page_redirect():
    """Redirect to homepage."""
    return redirect(url_for('home'))


# ---------------------------LOGIN/OUT---------------------------
@app.route('/login')
def login():
    """Login from."""
    if 'user' in session:
        current_user = session['user']
        return render_template('users/logged_in.html',
                               current_user=current_user)
    return render_template('users/login.html')


@app.route('/login/submit', methods=['POST'])
def login_submit():
    """Login submit."""
    current_user = None
    if 'user' in session:
        current_user = session['user']

    user = users.find_one({'username': request.form.get('username')})

    if user is None:
        return redirect(url_for('login'))
    if user['password'] != request.form.get('password'):
        return redirect(url_for('login'))

    data = {
        'username': request.form.get('username'),
        'user_id': str(user['_id'])
    }

    session['user'] = json.loads(json_util.dumps(data))

    current_user = session['user']
    return redirect(url_for('home', current_user=current_user))


@app.route('/logout')
def logout():
    """Remove user from session."""
    # session.pop('user', None)
    session.clear()
    return redirect(url_for('home'))


# ---------------------------USERS---------------------------
@app.route('/users/new')
def users_new():
    """Return a user creation page with starter Ranchos."""
    if 'user' in session:
        current_user = session['user']
        return render_template('users/logged_in.html',
                               current_user=current_user)
    return render_template('users/new_user.html', user={}, title='New User')


@app.route('/users/directory')
def users_directory():
    """Return a directory of users."""
    current_user = None
    if 'user' in session:
        current_user = session['user']

    # for user in users.find():
    #     users.update_one(
    #         {'_id': ObjectId(user['_id'])},
    #         {'$set': {'crikits': 200, 'last_paid': datetime.now()}})

    return render_template('users/users_directory.html', users=users.find(),
                           current_user=current_user)


@app.route('/users', methods=['POST'])
def users_submit():
    """Submit a new user."""
    if 'user' in session:
        current_user = session['user']
        return render_template('users/logged_in.html',
                               current_user=current_user)

    if users.find_one({'username': request.form.get('username')}) is not None:
        return redirect(url_for('users_new'))

    user = {
        'username': request.form.get('username'),
        'password': request.form.get('password'),
        'bio': request.form.get('content'),
        'created_at': datetime.now(),
        'crikits': 200,
        'last_paid': datetime.now()
    }

    user_id = users.insert_one(user).inserted_id

    data = {
        'username': request.form.get('username'),
        'user_id': str(user_id)
    }

    session['user'] = json.loads(json_util.dumps(data))
    # print(user_id)
    # print(users.find_one({'username': request.form.get('username')})['_id'])
    # print(session['user']['user_id'])
    return redirect(url_for('users_show', user_id=user_id))


@app.route('/users/<user_id>/edit')
@login_required
def users_edit(user_id):
    """Show the edit form for a user profile."""
    current_user = session['user']

    user = users.find_one({'_id': ObjectId(user_id)})

    if ObjectId(current_user['user_id']) != user['_id']:
        return render_template('go_back.html', current_user=current_user)

    return render_template('users/users_edit.html', user=user,
                           title='Edit User Profile',
                           current_user=current_user)


@app.route('/daily_crikits')
@login_required
def daily_crikits():
    """Pay daily 25 crikits."""
    current_user = session['user']
    usid = current_user['user_id']

    a_user = users.find_one({'_id': ObjectId(current_user['user_id'])})
    timediff = datetime.now() - a_user['last_paid']
    if timediff.days >= 1:
        new_balance = a_user['crikits'] + 25
        users.update_one(
            {'_id': ObjectId(current_user['user_id'])},
            {'$set': {'crikits': new_balance, 'last_paid': datetime.now()}})
        return redirect(url_for('users_show', user_id=usid))

    error = {
        'error_message': "You've already claimed your daily reward in the last 24 hours.",
        'error_link': '/',
        'back_message': 'Back to home?'
    }
    return render_template('error_message.html', error=error, current_user=current_user)


@app.route('/users/<user_id>', methods=['POST'])
@login_required
def users_update(user_id):
    """Submit an edited user profile."""
    current_user = session['user']

    if ObjectId(current_user['user_id']) != ObjectId(user_id):
        return render_template('go_back.html', current_user=current_user)

    updated_user = {
        'bio': request.form.get('content')
    }

    users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': updated_user})
    return redirect(url_for('users_show', user_id=user_id))


@app.route('/users/<user_id>')
def users_show(user_id):
    """Show a single user page."""
    current_user = None

    if 'user' in session:
        current_user = session['user']

    user = users.find_one({'_id': ObjectId(user_id)})
    print(user['crikits'])

    user_ranchos = ranchos.find({'user_id': ObjectId(user_id)})
    return render_template('users/users_show.html', user=user,
                           ranchos=user_ranchos,
                           current_user=current_user)


@app.route('/users/<user_id>/delete', methods=['POST'])
@login_required
def users_delete(user_id):
    """Delete one user."""
    current_user = session['user']

    if ObjectId(current_user['user_id']) != ObjectId(user_id):
        return render_template('go_back.html', current_user=current_user)

    users.delete_one({'_id': ObjectId(user_id)})

    session.clear()  # Clear Session

    return redirect(url_for('users_directory'))


# ---------------------------LISTINGS---------------------------
@app.route('/listings_home')
def listings_home():
    """Return listings homepage."""
    current_user = None
    if 'user' in session:
        current_user = session['user']

    return render_template('/listings/listings_index.html',
                           listings=listings.find(), current_user=current_user)


@app.route('/listings/new')
@login_required
def listings_new():
    """Create a new listing."""
    current_user = session['user']

    return render_template('listings/new_listing.html',
                           listing={}, title='New Listing',
                           current_user=current_user)


@app.route('/listings', methods=['POST'])
@login_required
def listing_submit():
    """Submit a new listing."""
    current_user = session['user']
    listing = {
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'views': 0,
        'created_at': datetime.now(),
        'author': current_user['username'],
        'user_id': ObjectId(current_user['user_id'])
    }
    listing_id = listings.insert_one(listing).inserted_id
    return redirect(url_for('listings_show', listing_id=listing_id))


@app.route('/listings/<listing_id>')
def listings_show(listing_id):
    """Show a single listing."""
    current_user = None
    if 'user' in session:
        current_user = session['user']

    listing = listings.find_one({'_id': ObjectId(listing_id)})
    listing_comments = comments.find({'listing_id': ObjectId(listing_id)})
    listing_author = users.find({'_id': listing['user_id']})

    updated_views = {
        'views': listing['views'] + 1
    }
    listings.update_one(
        {'_id': ObjectId(listing_id)},
        {'$set': updated_views})

    return render_template('listings/listings_show.html', listing=listing,
                           comments=listing_comments, user=listing_author,
                           current_user=current_user)


@app.route('/listings/<listing_id>/edit')
@login_required
def listings_edit(listing_id):
    """Show the edit form for a listing."""
    current_user = session['user']
    listing = listings.find_one({'_id': ObjectId(listing_id)})

    if ObjectId(current_user['user_id']) != listing['user_id']:
        return render_template('go_back.html', current_user=current_user)

    return render_template('listings/listings_edit.html', listing=listing,
                           title='Edit Listing', current_user=current_user)


@app.route('/listings/<listing_id>', methods=['POST'])
@login_required
def listings_update(listing_id):
    """Submit an edited listing."""
    current_user = session['user']
    listing = listings.find_one({'_id': ObjectId(listing_id)})
    if ObjectId(current_user['user_id']) != listing['user_id']:
        return render_template('go_back.html', current_user=current_user)

    updated_listing = {
        'title': request.form.get('title'),
        'description': request.form.get('description')
    }
    listings.update_one(
        {'_id': ObjectId(listing_id)},
        {'$set': updated_listing})
    return redirect(url_for('listings_show', listing_id=listing_id))


@app.route('/listings/<listing_id>/delete', methods=['POST'])
@login_required
def listings_delete(listing_id):
    """Delete one listing."""
    current_user = session['user']
    listing = listings.find_one({'_id': ObjectId(listing_id)})
    if ObjectId(current_user['user_id']) != listing['user_id']:
        return render_template('go_back.html', current_user=current_user)

    listings.delete_one({'_id': ObjectId(listing_id)})
    return redirect(url_for('listings_home'))


# -------------------------RANCHOS (NOT IMPLEMENTED)-------------------------
@app.route('/ranchos/adoption_center')
@login_required
def adoption_center():
    """Show the adoption page with randomized ranchos."""
    current_user = session['user']
    rancho_species = ['Goliath Birdeater', 'Cobalt Blue']
    rancho_sex = ['Male', 'Female']
    ranchos_list = []

    for x in range(0, 9):
        rancho = {
            'species': choice(rancho_species),
            'sex': choice(rancho_sex),
            'stats': {
                'hardiness': randint(1, 100),
                'dexterity': randint(1, 100),
                'docility': randint(1, 100),
                'conformation': randint(1, 100),
            },
            'created_at': datetime.now()
        }
        ranchos_list.append(rancho)

    user_crikits = users.find_one({'username': current_user['username']})['crikits']

    return render_template('ranchos/adoption_center.html',
                           ranchos_list=ranchos_list,
                           current_user=current_user,
                           user_crikits=user_crikits)


@app.route('/ranchos/new', methods=['POST'])
@login_required
def ranchos_new():
    """Submit a new Rancho."""
    current_user = session['user']

    a_user = users.find_one({'_id': ObjectId(current_user['user_id'])})
    new_balance = a_user['crikits'] - 50
    if new_balance < 0:
        return render_template('go_back.html', current_user=current_user) 
    users.update_one(
        {'_id': ObjectId(current_user['user_id'])},
        {'$set': {'crikits': new_balance}})


    stats = {
        'hardiness': request.form.get('hardiness'),
        'dexterity': request.form.get('dexterity'),
        'docility': request.form.get('docility'),
        'conformation': request.form.get('conformation')
    }
    needs = {
        'food': 100,
        'water': 100,
        'health': 100,
        'happiness': 100,
        'last_cared': datetime.now(),
        'cared_by': current_user['username'],
        'cared_by_id': ObjectId(current_user['user_id'])
    }
    rancho = {
        'name': 'New Rancho',
        'bio': request.form.get('sex') + ' ' + request.form.get('species'),
        'adopted_at': datetime.now(),
        'xp': 1000,
        'level': level_calc(1000),
        'stats': stats,
        'needs': needs,
        'species': request.form.get('species'),
        'sex': request.form.get('sex'),
        'user_id': ObjectId(current_user['user_id'])
    }
    rancho_id = ranchos.insert_one(rancho).inserted_id

    return redirect(url_for('ranchos_edit', rancho_id=rancho_id))


@app.route('/ranchos/<rancho_id>')
def ranchos_show(rancho_id):
    """Show a single Rancho."""
    current_user = None
    if 'user' in session:
        current_user = session['user']
    rancho = ranchos.find_one({'_id': ObjectId(rancho_id)})

    # Update needs
    timediff = datetime.now() - rancho['needs']['last_cared']
    if timediff.days > 0:
        if timediff.days >= 4:
            # Been more than four days since last cared for
            new_needs = {
                'food': 0,
                'water': 0,
                'health': 0,
                'happiness': 0,
                'last_cared': rancho['needs']['last_cared'],
                'cared_by': rancho['needs']['cared_by'],
                'cared_by_id': rancho['needs']['cared_by_id']
            }

        elif timediff.days >= 3:
            # Been more than three days since last cared for

            new_needs = {
                'food': 25,
                'water': 0,
                'health': 50,
                'happiness': 0,
                'last_cared': rancho['needs']['last_cared'],
                'cared_by': rancho['needs']['cared_by'],
                'cared_by_id': rancho['needs']['cared_by_id']
            }

        elif timediff.days >= 2:
            # Been more than two days since last cared for
            new_needs = {
                'food': 50,
                'water': 0,
                'health': 100,
                'happiness': 50,
                'last_cared': rancho['needs']['last_cared'],
                'cared_by': rancho['needs']['cared_by'],
                'cared_by_id': rancho['needs']['cared_by_id']
            }

        elif timediff.days >= 1:
            # Been more than a day since last cared for
            new_needs = {
                'food': 75,
                'water': 50,
                'health': 100,
                'happiness': 75,
                'last_cared': rancho['needs']['last_cared'],
                'cared_by': rancho['needs']['cared_by'],
                'cared_by_id': rancho['needs']['cared_by_id']
            }
        ranchos.update_one(
            {'_id': ObjectId(rancho_id)},
            {'$set': {'needs': new_needs}}
            )

    return render_template('ranchos/ranchos_show.html', rancho=rancho,
                           current_user=current_user)


@app.route('/ranchos/<rancho_id>/care')
@login_required
def ranchos_care(rancho_id):
    """Care for a Rancho."""
    current_user = session['user']
    rancho = ranchos.find_one({'_id': ObjectId(rancho_id)})

    timediff = datetime.now() - rancho['needs']['last_cared']
    if timediff.days >= 1:
        # Been more than a day since last cared for
        new_health = rancho['needs']['health'] + 50
        if new_health > 100:
            new_health = 100

        new_needs = {
            'food': 100,
            'water': 100,
            'health': new_health,
            'happiness': 100,
            'last_cared': datetime.now(),
            'cared_by': current_user['username'],
            'cared_by_id': ObjectId(current_user['user_id'])
        }

        new_xp = rancho['xp'] + 250
        ranchos.update_one(
            {'_id': ObjectId(rancho_id)},
            {'$set': {
                'needs': new_needs,
                'xp': new_xp,
                'level': level_calc(new_xp)
                }}
            )
    # Can care for other people's Ranchos
    # if ObjectId(current_user['user_id']) != rancho['user_id']:
    #     return render_template('go_back.html', current_user=current_user)

    return redirect(url_for('ranchos_show', rancho_id=rancho_id))


@app.route('/ranchos/<rancho_id>/edit')
@login_required
def ranchos_edit(rancho_id):
    """Show the edit form for a Rancho profile."""
    current_user = session['user']
    rancho = ranchos.find_one({'_id': ObjectId(rancho_id)})

    if ObjectId(current_user['user_id']) != rancho['user_id']:
        return render_template('go_back.html', current_user=current_user)

    return render_template('ranchos/ranchos_edit.html', rancho=rancho,
                           title='Edit Rancho Profile',
                           current_user=current_user)


@app.route('/ranchos/<rancho_id>', methods=['POST'])
@login_required
def ranchos_update(rancho_id):
    """Submit an edited rancho profile."""
    current_user = session['user']
    rancho = ranchos.find_one({'_id': ObjectId(rancho_id)})
    if ObjectId(current_user['user_id']) != rancho['user_id']:
        return render_template('go_back.html', current_user=current_user)

    updated_prof = {
        'name': request.form.get('rancho_name'),
        'bio': request.form.get('description')
    }
    ranchos.update_one(
        {'_id': ObjectId(rancho_id)},
        {'$set': updated_prof})
    return redirect(url_for('ranchos_show', rancho_id=rancho_id))


@app.route('/ranchos/<rancho_id>/release', methods=['POST'])
@login_required
def ranchos_delete(rancho_id):
    """Release (delete) one Rancho."""
    current_user = session['user']
    rancho = ranchos.find_one({'_id': ObjectId(rancho_id)})

    if ObjectId(current_user['user_id']) != rancho['user_id']:
        return render_template('go_back.html', current_user=current_user)

    ranchos.delete_one({'_id': ObjectId(rancho_id)})

    a_user = users.find_one({'_id': ObjectId(current_user['user_id'])})
    new_balance = a_user['crikits'] + 25
    users.update_one(
        {'_id': ObjectId(current_user['user_id'])},
        {'$set': {'crikits': new_balance}})

    return redirect(url_for('users_show',
                            user_id=rancho.get('user_id')))

# ---------------------------COMMENTS---------------------------
@app.route('/listings/comments', methods=['POST'])
@login_required
def comments_new():
    """Submit a new comment."""
    current_user = session['user']
    comment = {
        'title': request.form.get('title'),
        'content': request.form.get('content'),
        'listing_id': ObjectId(request.form.get('listing_id')),
        'author': current_user['username'],
        'user_id': ObjectId(current_user['user_id'])
    }
    comments.insert_one(comment)
    return redirect(url_for('listings_show',
                            listing_id=request.form.get('listing_id')))


@app.route('/listings/comments/<comment_id>', methods=['POST'])
@login_required
def comments_delete(comment_id):
    """Delete a comment."""
    current_user = session['user']
    comment = comments.find_one({'_id': ObjectId(comment_id)})

    if ObjectId(current_user['user_id']) != comment['user_id']:
        return render_template('go_back.html', current_user=current_user)

    comments.delete_one({'_id': ObjectId(comment_id)})
    return redirect(url_for('listings_show',
                            listing_id=comment.get('listing_id')))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
