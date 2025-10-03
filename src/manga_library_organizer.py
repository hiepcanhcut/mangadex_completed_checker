import requests
import time

# ==== Nhập thông tin của bạn ở đây ====
CLIENT_ID = os.getenv("MANGADEX_CLIENT_ID") or input("Client ID: ")
CLIENT_SECRET = os.getenv("MANGADEX_CLIENT_SECRET") or input("Client Secret: ")
USERNAME = os.getenv("MANGADEX_USERNAME") or input("Username: ")
PASSWORD = os.getenv("MANGADEX_PASSWORD") or input("Password: ")

def get_token():
    try:
        print("Đang lấy token...")
        url = "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": USERNAME,
            "password": PASSWORD
        }
        r = requests.post(url, data=data)
        r.raise_for_status()
        token = r.json()["access_token"]
        print("✓ Lấy token thành công")
        return token
    except Exception as e:
        print(f"✗ Lỗi khi lấy token: {e}")
        return None

def get_all_followed_manga(token):
    """Lấy tất cả manga đang follow và trạng thái của chúng"""
    all_manga = []
    offset = 0
    limit = 100
    
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        print(f"Đang lấy danh sách manga (offset: {offset})...")
        url = f"https://api.mangadex.org/user/follows/manga"
        params = {
            "limit": limit,
            "offset": offset,
            "includes[]": ["manga"]
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Lỗi khi lấy danh sách: {response.text}")
            break
            
        data = response.json()
        
        if "data" not in data or len(data["data"]) == 0:
            break
            
        # Xử lý từng manga
        for item in data["data"]:
            manga_id = item["id"]
            
            # Lấy thông tin chi tiết của manga
            manga_info = get_manga_details(manga_id, token)
            if manga_info:
                all_manga.append(manga_info)
        
        offset += limit
        time.sleep(0.5)  # Tránh rate limit
    
    return all_manga

def get_manga_details(manga_id, token):
    """Lấy thông tin chi tiết của manga"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.mangadex.org/manga/{manga_id}"
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        data = response.json()
        attributes = data["data"]["attributes"]
        
        # Lấy tên manga
        title = attributes["title"].get("en", 
                attributes["title"].get("ja", 
                attributes["title"].get("ko", "Unknown Title")))
        
        # Lấy trạng thái (completed hoặc ongoing)
        status = attributes.get("status", "ongoing")
        
        # Lấy status hiện tại trong thư viện của user
        library_status = get_library_status(manga_id, token)
        
        return {
            "id": manga_id,
            "title": title,
            "manga_status": status,  # Trạng thái thực tế của manga
            "library_status": library_status  # Trạng thái trong thư viện
        }
    except Exception as e:
        print(f"Lỗi khi lấy thông tin manga {manga_id}: {e}")
        return None

def get_library_status(manga_id, token):
    """Lấy trạng thái hiện tại của manga trong thư viện user"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.mangadex.org/manga/{manga_id}/status"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("status", "reading")
        return "reading"
    except:
        return "reading"

def update_manga_status(manga_id, token, new_status):
    """Cập nhật trạng thái của manga trong thư viện"""
    try:
        url = f"https://api.mangadex.org/manga/{manga_id}/status"
        headers = {
            "Authorization": f"Bearer {token}", 
            "Content-Type": "application/json"
        }
        data = {"status": new_status}
        
        response = requests.post(url, headers=headers, json=data)
        return response.status_code in (200, 204)
    except Exception as e:
        print(f"Lỗi khi cập nhật status: {e}")
        return False

def main():
    print("Bắt đầu kiểm tra và phân loại truyện...")
    
    token = get_token()
    if not token:
        return
    
    # Lấy tất cả manga đang follow
    manga_list = get_all_followed_manga(token)
    
    if not manga_list:
        print("Không tìm thấy truyện nào trong thư viện!")
        return
    
    print(f"\nĐã tìm thấy {len(manga_list)} truyện trong thư viện")
    
    completed_count = 0
    reading_count = 0
    already_correct = 0
    
    print("\nĐang kiểm tra và cập nhật trạng thái...")
    
    for manga in manga_list:
        title = manga["title"]
        manga_status = manga["manga_status"]  # Trạng thái thực tế
        current_library_status = manga["library_status"]  # Trạng thái hiện tại trong thư viện
        
        print(f"\nĐang xử lý: {title}")
        print(f"  - Trạng thái thực tế: {manga_status}")
        print(f"  - Trạng thái hiện tại trong thư viện: {current_library_status}")
        
        # Quyết định trạng thái mới
        if manga_status == "completed":
            new_status = "completed"
            status_text = "completed"
        else:
            new_status = "reading" 
            status_text = "reading"
        
        # Chỉ cập nhật nếu trạng thái thay đổi
        if current_library_status != new_status:
            success = update_manga_status(manga["id"], token, new_status)
            if success:
                print(f"  ✓ Đã chuyển sang: {status_text}")
                if new_status == "completed":
                    completed_count += 1
                else:
                    reading_count += 1
            else:
                print(f"  ✗ Lỗi khi cập nhật")
        else:
            print(f"  ✓ Đã đúng trạng thái: {status_text}")
            already_correct += 1
        
        time.sleep(0.3)  # Tránh rate limit
    
    print(f"\n=== KẾT QUẢ ===")
    print(f"Tổng số truyện: {len(manga_list)}")
    print(f"Đã chuyển sang completed: {completed_count}")
    print(f"Đã chuyển sang reading: {reading_count}")
    print(f"Đã đúng trạng thái: {already_correct}")

if __name__ == "__main__":
    main()
