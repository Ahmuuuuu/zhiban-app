<template>
   <!-- 左侧侧边栏 -->
      <aside class="sidebar">
        <div class="logo-area">
          <div class="logo-icon"></div>
          <div class="brand">知伴</div>
        </div>

        <!-- //首页 -->
        <nav class="menu">
          <router-link to="/"  class="menu-item">
   <div >
            <span class="menu-icon"><img src="../assets/pic/Homepage.svg" ></span>
            <span>首页</span>
          </div>

          </router-link>
          
        </nav>

        <!-- ai对话 -->
        <nav class="menu">
          <router-link to="/chat"  class="menu-item">
           <div>
             <span class="menu-icon">
              <img src="../assets/pic/message.svg" >
            </span>
            <span>ai对话</span>
          </div>

          </router-link>
            
          
        </nav>

        
         

        <!-- //学习路径 -->
         <nav class="menu">
          <router-link to="/mine" class="menu-item">

             <div
           
            
          >
            <span class="menu-icon"><img src="../assets/pic/other.svg" ></span>
            <span>我的</span>
          </div>
          </router-link>
         
        </nav>
        <nav class="menu">
          <router-link to="/profile" class="menu-item">
            <div>
              <span class="menu-icon"><img src="../assets/pic/yonghuhuaxiang.svg" ></span>
              <span>个人中心</span>
            </div>
          </router-link>
        </nav>

        <div class="sidebar-bottom">
          <router-link to="/profile" class="avatar-link" aria-label="个人中心">
            <div class="small-avatar"></div>
          </router-link>
        </div>
      </aside>
</template>

<script>
export default {
  name:'Navigation'
}
</script>

<style>
/* 左侧导航 */
.sidebar {
  background: #f0efdd;
  border-right: 1px solid #c9dce9;
  padding: 28px 18px;
  display: flex;
  flex-direction: column;
  
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 34px;
}

.logo-icon {
  width: 28px;
  height: 28px;
  border: 3px solid #163f8f;
  border-radius: 8px;
  transform: rotate(45deg);
}

.brand {
  font-size: 24px;
  font-weight: 800;
  color: #163f8f;
}

.menu {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap:12px;
  
}

.menu-item {
  height: 30px;
  width: 120px;
  border-radius: 8px;
  padding: 0 20px;
  margin: 10px;
  display: flex;
  align-items: center;
  gap:12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  color: #163f8f;
  transition: all 0.25s ease;
}

.menu-item.router-link-active {
  background: #c9dce9;
  transform: translateX(6px) scale(1.03);
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  
}
.menu-item:hover {
  background: #c9dce9;
  transform: translateX(6px) scale(1.03);
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);

}

.menu-icon {
  
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
   transform: translate(-10px, 4px);
}

.menu-icon img {
  width: 100%;
  height: 100%;
  display: block;
}

.sidebar-bottom {
  margin-top: auto;
  display: flex;
  justify-content: center;
}

.avatar-link {
  display: inline-flex;
  border-radius: 50%;
  transition: transform 0.25s ease;
}

.avatar-link:hover {
  transform: scale(1.06);
}

.small-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #d9c7b8, #f3e7dd);
}
</style>
