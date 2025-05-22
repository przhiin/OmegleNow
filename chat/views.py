from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import uuid
import json

# In-memory storage (not suitable for production)
waiting_list = []
active_chats = {}
chat_messages = {}
pending_matches = {}
skipped_partners = {}

# In-memory storage for video chat
video_waiting_list = []
video_active_chats = {}
video_pending_matches = {}

# Home page with mode selection
def home(request):
    context = {
        'active_chat_count': len(active_chats),
        'waiting_list_count': len(waiting_list),
        'active_users' : len(waiting_list) + len(active_chats)
    }
    return render(request, 'chat/home.html', context)

# Text chat main page
def text_chat_page(request):
    return render(request, 'chat/text_chat.html')

# Video call main page
def video_chat_page(request):
    return render(request, 'chat/video_chat.html')

# Matchmaking endpoint for text chat




def perform_matchmaking(user_id):
    now = time.time()
    for user in list(waiting_list):
        if user['id'] != user_id:   
            waiting_list.remove(user)
            room_id = str(uuid.uuid4())
            active_chats[room_id] = [user['id'], user_id]

            # Remove both users from waiting list
            waiting_list[:] = [u for u in waiting_list if u['id'] not in [user_id, user['id']]]

            # Set up pending matches
            pending_matches[user['id']] = (room_id, user_id)
            pending_matches[user_id] = (room_id, user['id'])

            return {
                "status": "connected",
                "chat_room": room_id,
                "partner_id": user['id']
            }

    # If no match found, put user in waiting list
    waiting_list[:] = [u for u in waiting_list if u['id'] != user_id]
    if not user_id:
        user_id = str(uuid.uuid4())
    
    if not any(u['id'] == user_id for u in waiting_list):
        waiting_list.append({'id': user_id})

    return {
        "status": "waiting",
        "user_id": user_id
    }   



@csrf_exempt
def find_match(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data.get("id")

        # Check if the user already has a pending match
        if user_id in pending_matches:
            room_id, partner_id = pending_matches.pop(user_id)
            return JsonResponse({
                "status": "connected",
                "chat_room": room_id,
                "partner_id": partner_id
            })

        result = perform_matchmaking(user_id)
        return JsonResponse(result)
    
import time

# Track last seen time
last_active = {}

@csrf_exempt
def ping(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get("id")
        if user_id:
            last_active[user_id] = time.time()
            return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)


def cleanup_inactive_users():
    now = time.time()
    inactive = [uid for uid, ts in last_active.items() if now - ts > 30]

    for user_id in inactive:
        last_active.pop(user_id, None)
        # Remove from waiting list
        waiting_list[:] = [u for u in waiting_list if u['id'] != user_id]
        # Remove from pending matches
        pending_matches.pop(user_id, None)
        # Remove from active chats
        for room, users in list(active_chats.items()):
            if user_id in users:
                active_chats.pop(room)
                for u in users:
                    if u != user_id:
                        skipped_partners[u] = user_id



# Text chat room view
def chat_room(request, room_id):
    if room_id not in active_chats:
        return redirect('home')
    return render(request, 'chat/chat_room.html')

def get_messages(request, room_id):
    messages = chat_messages.get(room_id, [])
    response = {'messages': messages}
    user_id = request.GET.get('user')

    if user_id in skipped_partners:
        response['skipped_by_partner'] = True
        response['skipped_by'] = skipped_partners.pop(user_id)

    return JsonResponse(response)

# Send message to chat room
@csrf_exempt
def send_message(request, room_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = data.get("user")
        text = data.get("text")
        if room_id in chat_messages:
            chat_messages[room_id].append({"user": user, "text": text})
        else:
            chat_messages[room_id] = [{"user": user, "text": text}]
        return JsonResponse({'status': 'success'})

# Skip text chat partner
@csrf_exempt
def skip_user(request, room_id):
    if request.method == "POST" and room_id in active_chats:
        data = json.loads(request.body)
        skipper = data.get("id")
        participants = active_chats.pop(room_id)          # e.g. ['Alice', 'Bob']

        # figure out who got skipped
        if skipper == participants[0]:
            other = participants[1]
        else:
            other = participants[0]

        # clear any leftover pending matches
        pending_matches.pop(skipper, None)
        pending_matches.pop(other, None)

        # mark the other person as “skipped”
        skipped_partners[other] = skipper

        # optional: reset or clear chat_messages[room_id]
        chat_messages.pop(room_id, None)


        # re-enqueue both, as fresh users
        perform_matchmaking(skipper)
        perform_matchmaking(other)

        return JsonResponse({
            "status": "skipped",
            "skipped_by": skipper,
            "partner_id": other
        })

    return JsonResponse({"status": "error", "message": "Invalid room"})


# def skip_user(request, room_id):
#     if room_id in active_chats:
#         partner_name = active_chats[room_id][1]
#         skipped_by = active_chats[room_id][0]

#         chat_messages[room_id] = [{"user": "system", "text": f"{skipped_by} skipped you. Search for another partner!"}]
#         skipped_partners[partner_name] = skipped_by
#         del active_chats[room_id]

#         return JsonResponse({'status': 'skipped', 'skipped_by': skipped_by, 'partner_name': partner_name})
#     return JsonResponse({'status': 'error', 'message': 'Invalid room'})

# ==============================
# VIDEO CHAT SECTION STARTS HERE
# ==============================
# Find a video call match
@csrf_exempt
def find_video_match(request):
    print("find_video_match called")
    import sys
    sys.stdout.flush()

    if request.method == "POST":
        data = json.loads(request.body)
        user_name = data.get("name")
        user_id = str(uuid.uuid4())

        # First, check if already matched
        if user_name in video_pending_matches:
            room_id, partner_name = video_pending_matches.pop(user_name)
            return JsonResponse({
                "status": "connected",
                "chat_room": room_id,
                "partner_name": partner_name
            })

        # Clean waiting list: remove duplicates and stale users
        video_waiting_list[:] = [
            user for user in video_waiting_list
            if user['name'] != user_name
        ]

        # Try to find a partner
        for user in list(video_waiting_list):
            if user['name'] != user_name:
                video_waiting_list.remove(user)
                room_id = str(uuid.uuid4())
                video_active_chats[room_id] = [user['name'], user_name]

                video_pending_matches[user['name']] = (room_id, user_name)

                return JsonResponse({
                    "status": "connected",
                    "chat_room": room_id,
                    "partner_name": user['name']
                })

        # No match found, add this user to waiting list
        video_waiting_list.append({'name': user_name, 'id': user_id})
        print("Video waiting list updated:", video_waiting_list)
        sys.stdout.flush()

        return JsonResponse({"status": "waiting", "user_id": user_id})

# Video chat room view (for when two users are matched)
# Text chat room view
from django.shortcuts import render, redirect

def video_chat_room(request, room_id):
    user_id = request.GET.get("user_id", "")
    partner_name = request.GET.get("partner_name", "")
    return render(request, 'chat/video_chat_room.html', {
        'room_id': room_id,
        'user_id': user_id,
        'partner_name': partner_name
    })


# Skip video partner (if user wants to disconnect)
# def skip_video_partner(request, room_id):
#     if room_id in active_chats:
#         del active_chats[room_id]
#     return redirect('home')

# Skip video chat partner
@csrf_exempt
def skip_video_partner(request, room_id):
    if room_id in video_active_chats:
        data = json.loads(request.body)
        skipper = data.get("user")
        user1, user2 = video_active_chats[room_id]

        # Identify the partner who is skipped
        partner = user2 if skipper == user1 else user1

        # Notify partner they were skipped (you can add real-time notifications here)
        video_active_chats.pop(room_id, None)

        # Clean up stale entries from waiting list and pending matches
        video_waiting_list[:] = [u for u in video_waiting_list if u['name'] not in [user1, user2]]
        video_pending_matches.pop(user1, None)
        video_pending_matches.pop(user2, None)

        # Add both users back to the waiting list
        video_waiting_list.append({'name': user1, 'id': str(uuid.uuid4())})
        video_waiting_list.append({'name': user2, 'id': str(uuid.uuid4())})

        # Return the response with a message
        return JsonResponse({
            'status': 'skipped',
            'skipped_by': skipper,
            'partner_name': partner
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid room'})
