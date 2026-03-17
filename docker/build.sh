#!/bin/bash
# ============================================================
#  build.sh — Build Docker image + ROS2 workspace
#
#  วิธีใช้บน Pi (2 แบบ):
#
#  แบบที่ 1 — clone จาก GitHub แล้ว build เลย:
#    curl -fsSL https://raw.githubusercontent.com/Bank6452/Final-Project-automation-mower/main/docker/build.sh | bash
#
#  แบบที่ 2 — อยู่ใน folder แล้ว:
#    bash docker/build.sh
# ============================================================

set -e

# ---- สี terminal ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ---- ตัวแปร ----
REPO_URL="https://github.com/Bank6452/Final-Project-automation-mower.git"
REPO_DIR="$HOME/mower_ws"
IMAGE_NAME="mower_bot"
IMAGE_TAG="humble"

# ---- parse args ----
BUILD_DOCKER=true
BUILD_ROS=true
NO_CACHE=false
SKIP_CLONE=false

for arg in "$@"; do
  case $arg in
    --docker-only)  BUILD_ROS=false ;;
    --ros-only)     BUILD_DOCKER=false ;;
    --no-cache)     NO_CACHE=true ;;
    --skip-clone)   SKIP_CLONE=true ;;
    --help|-h)
      echo "Usage: bash docker/build.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --docker-only   Build Docker image เท่านั้น"
      echo "  --ros-only      Build ROS2 packages ใน container เท่านั้น"
      echo "  --no-cache      Build Docker โดยไม่ใช้ cache"
      echo "  --skip-clone    ข้ามขั้นตอน git clone/pull"
      exit 0 ;;
  esac
done

# ============================================================
#  STEP 1: ตรวจสอบ dependencies
# ============================================================
info "ตรวจสอบ dependencies..."

command -v docker &>/dev/null  || error "ไม่พบ docker — ติดตั้งด้วย: curl -fsSL https://get.docker.com | sh"
command -v git    &>/dev/null  || error "ไม่พบ git — ติดตั้งด้วย: sudo apt install git"
docker compose version &>/dev/null || warn "ไม่พบ 'docker compose' v2 (optional)"

success "Dependencies ครบ"

# ============================================================
#  STEP 2: Clone หรือ Pull จาก GitHub
# ============================================================
if [ "$SKIP_CLONE" = false ]; then
  if [ -d "$REPO_DIR/.git" ]; then
    info "พบ repo อยู่แล้วที่ $REPO_DIR — กำลัง pull..."
    git -C "$REPO_DIR" pull origin main
  else
    info "กำลัง clone repo จาก GitHub..."
    info "  → $REPO_URL"
    info "  → $REPO_DIR"
    git clone "$REPO_URL" "$REPO_DIR"
  fi
  success "Git sync เสร็จสิ้น"
else
  info "ข้ามขั้นตอน git clone (--skip-clone)"
fi

# หา workspace directory
if [ -f "$(pwd)/Dockerfile" ]; then
  WORKSPACE_DIR="$(pwd)"           # รันจาก root ของ repo
elif [ -f "$(pwd)/../Dockerfile" ]; then
  WORKSPACE_DIR="$(cd "$(pwd)/.." && pwd)"   # รันจาก docker/
elif [ -d "$REPO_DIR" ]; then
  WORKSPACE_DIR="$REPO_DIR"        # ใช้จาก clone path
else
  error "ไม่พบ Dockerfile — กรุณา cd ไปที่ root ของ project ก่อน"
fi

info "Workspace: $WORKSPACE_DIR"

# ============================================================
#  STEP 3: Build Docker image
# ============================================================
if [ "$BUILD_DOCKER" = true ]; then
  info "กำลัง build Docker image: ${IMAGE_NAME}:${IMAGE_TAG}..."

  CACHE_FLAG=""
  [ "$NO_CACHE" = true ] && CACHE_FLAG="--no-cache" && warn "ใช้โหมด --no-cache"

  docker build \
    $CACHE_FLAG \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --file "$WORKSPACE_DIR/Dockerfile" \
    "$WORKSPACE_DIR"

  success "Build Docker image สำเร็จ: ${IMAGE_NAME}:${IMAGE_TAG}"
  echo ""
  docker images "${IMAGE_NAME}:${IMAGE_TAG}"
  echo ""
fi

# ============================================================
#  STEP 4: Build ROS2 packages ใน container
# ============================================================
if [ "$BUILD_ROS" = true ]; then
  info "กำลัง build ROS2 packages ใน container..."
  info "Packages: mower_bot_description, robot_bridge"

  docker run --rm \
    --volume "$WORKSPACE_DIR/src:/ros2_ws/src:ro" \
    --volume "$WORKSPACE_DIR/install:/ros2_ws/install" \
    --volume "$WORKSPACE_DIR/build:/ros2_ws/build" \
    --volume "$WORKSPACE_DIR/log:/ros2_ws/log" \
    "${IMAGE_NAME}:${IMAGE_TAG}" \
    bash -c "
      set -e
      source /opt/ros/humble/setup.bash
      cd /ros2_ws
      echo '[colcon] เริ่ม build...'
      colcon build \
        --packages-select mower_bot_description robot_bridge \
        --symlink-install \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
        --event-handlers console_cohesion+
      echo '[colcon] Build เสร็จสิ้น'
    "

  success "Build ROS2 packages สำเร็จ"
  info "ผลลัพธ์อยู่ที่: $WORKSPACE_DIR/install/"
fi

# ============================================================
#  DONE
# ============================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Build เสร็จสมบูรณ์!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "วิธีรัน:"
echo "  cd $WORKSPACE_DIR"
echo "  docker compose up hardware    # serial + RealSense + GPS"
echo "  docker compose up localize    # EKF localization"
echo "  docker compose up navigation  # Nav2"
echo "  docker compose run --rm shell # bash debug"
echo ""
