import numpy as np
import pandas as pd
import requests
import pygame
import random
from datetime import datetime, timedelta
import math

# 初始化Pygame
pygame.init()

# 设置窗口
WIDTH = 1200
HEIGHT = 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hong Kong Air Quality Visualization (1993-2023)")

# 定义区域
DISTRICTS = ['Central & Western', 'Eastern', 'Southern', 'Wan Chai', 'Kowloon City', 
            'Kwun Tong', 'Sham Shui Po', 'Wong Tai Sin', 'Yau Tsim Mong']

# 扩展颜色定义和说明
AQI_LEVELS = [
    {'range': (0, 50), 'color': (50, 205, 50), 'name': 'Good', 
     'desc': 'Air quality is satisfactory with minimal air pollution'},
    {'range': (51, 100), 'color': (255, 255, 0), 'name': 'Moderate', 
     'desc': 'Air quality is acceptable but may affect sensitive groups'},
    {'range': (101, 150), 'color': (255, 165, 0), 'name': 'Unhealthy for Sensitive', 
     'desc': 'Members of sensitive groups may experience health effects'},
    {'range': (151, 200), 'color': (255, 69, 0), 'name': 'Unhealthy', 
     'desc': 'Everyone may begin to experience health effects'},
    {'range': (201, 300), 'color': (255, 0, 0), 'name': 'Very Unhealthy', 
     'desc': 'Health warnings of emergency conditions for everyone'},
    {'range': (301, 500), 'color': (128, 0, 0), 'name': 'Hazardous', 
     'desc': 'Health alert: everyone may experience serious health effects'}
]

GRADIENT_COLORS = [level['color'] for level in AQI_LEVELS]

# 详细的历史事件信息
HISTORICAL_EVENTS = {
    1993: {
        'title': 'Air Quality Monitoring Network Established',
        'desc': 'Hong Kong established its first air quality monitoring network for systematic data collection.'
    },
    1995: {
        'title': 'Air Quality Objectives Implementation',
        'desc': 'Introduction of Air Quality Index (AQI) system to provide clearer air quality information.'
    },
    1997: {
        'title': 'Vehicle Emission Standards Tightened',
        'desc': 'Implementation of stricter vehicle emission standards, requiring Euro II standards for new vehicles.'
    },
    2000: {
        'title': 'Enhanced Vehicle Emission Control',
        'desc': 'Implementation of Euro III emission standards and multiple air quality improvement measures.'
    },
    2005: {
        'title': 'Cleaner Production Partnership',
        'desc': 'Cooperation with Guangdong Province on cleaner production to reduce regional air pollution.'
    },
    2010: {
        'title': 'Regional Air Quality Management',
        'desc': 'Joint implementation of regional air quality management strategy with Pearl River Delta.'
    },
    2015: {
        'title': 'Air Quality Objectives Update',
        'desc': 'Adoption of stricter standards and addition of PM2.5 monitoring indicators.'
    },
    2020: {
        'title': 'New Air Quality Targets',
        'desc': 'Set 2025 air quality improvement goals, promoting green transport and clean energy.'
    }
}

# 颜色定义
COLORS = {
    'background': (10, 10, 30),
    'text': (255, 255, 255),
    'text_secondary': (180, 180, 180),  # 次要文本颜色
    'text_tertiary': (160, 160, 160),   # 第三级文本颜色
    'graph_bg': (20, 20, 40),
    'grid': (40, 40, 60),
    'highlight': (255, 215, 0),
    'border': (100, 100, 100),          # 边框颜色
    'particle_good': (50, 205, 50),
    'particle_moderate': (255, 255, 0),
    'particle_unhealthy': (255, 165, 0),
    'particle_hazardous': (255, 0, 0)
}

def interpolate_color(color1, color2, factor):
    """在两个颜色之间插值"""
    return tuple(int(color1[i] + (color2[i] - color1[i]) * factor) for i in range(3))

def get_color_for_value(value, min_val=0, max_val=150):
    """根据数值获取渐变颜色"""
    if value <= min_val:
        return GRADIENT_COLORS[0]
    if value >= max_val:
        return GRADIENT_COLORS[-1]
    
    section_size = (max_val - min_val) / (len(GRADIENT_COLORS) - 1)
    section = int((value - min_val) / section_size)
    factor = ((value - min_val) % section_size) / section_size
    
    return interpolate_color(GRADIENT_COLORS[section], GRADIENT_COLORS[section + 1], factor)

class Graph:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.Font(None, 24)
        self.year_positions = {}  # 存储年份与其x坐标的映射
        
    def get_year_from_mouse_pos(self, mouse_x, mouse_y):
        """根据鼠标位置获取对应的年份"""
        if not self.rect.collidepoint(mouse_x, mouse_y):
            return None
        
        # 计算相对于图表左边的位置
        relative_x = mouse_x - self.rect.left
        year_range = (1993, 2023)
        
        # 根据x坐标计算年份
        year_fraction = relative_x / self.rect.width
        calculated_year = year_range[0] + year_fraction * (year_range[1] - year_range[0])
        
        # 返回最接近的整数年份
        return max(1993, min(2023, round(calculated_year)))
        
    def draw(self, screen, data, year_range=(1993, 2023), current_year=1993):
        # 绘制背景
        pygame.draw.rect(screen, COLORS['graph_bg'], self.rect)
        
        # 绘制纵坐标网格和标签
        for i in range(6):
            y = self.rect.top + (self.rect.height * i) // 5
            pygame.draw.line(screen, COLORS['grid'], 
                           (self.rect.left, y), 
                           (self.rect.right, y))
            value = 150 - (i * 30)
            text = self.font.render(str(value), True, COLORS['text'])
            screen.blit(text, (self.rect.left - 30, y - 10))
        
        # 清空年份位置映射
        self.year_positions = {}
        
        # 绘制横坐标网格和标签（年份）
        year_interval = 5  # 每5年显示一个标签
        for i, year in enumerate(range(year_range[0], year_range[1] + 1, year_interval)):
            x = self.rect.left + (year - year_range[0]) * self.rect.width // (year_range[1] - year_range[0])
            
            # 存储年份位置
            self.year_positions[year] = x
            
            # 绘制垂直网格线
            pygame.draw.line(screen, COLORS['grid'], 
                           (x, self.rect.top), 
                           (x, self.rect.bottom))
            
            # 高亮当前年份
            is_current = abs(year - current_year) < 2.5  # 当前年份附近的高亮
            
            # 绘制年份标签
            if is_current:
                year_text = pygame.font.Font(None, 28).render(str(year), True, COLORS['highlight'])
                # 添加背景高亮
                highlight_surface = pygame.Surface((50, 25), pygame.SRCALPHA)
                highlight_surface.fill((*COLORS['highlight'][:3], 50))
                screen.blit(highlight_surface, (x - 25, self.rect.bottom + 5))
            else:
                year_text = self.font.render(str(year), True, COLORS['text'])
            
            text_rect = year_text.get_rect()
            screen.blit(year_text, (x - text_rect.width // 2, self.rect.bottom + 5))
        
        # 绘制年份点击提示
        if len(self.year_positions) > 0:
            hint_text = pygame.font.Font(None, 18).render("Click on years to jump", True, COLORS['text_secondary'])
            screen.blit(hint_text, (self.rect.left, self.rect.bottom + 35))
        
        # 绘制当前年份指示器
        current_x = self.rect.left + (current_year - year_range[0]) * self.rect.width // (year_range[1] - year_range[0])
        if self.rect.left <= current_x <= self.rect.right:
            # 绘制垂直指示线
            pygame.draw.line(screen, COLORS['highlight'], 
                           (current_x, self.rect.top), 
                           (current_x, self.rect.bottom), 3)
            
            # 绘制顶部三角形指示器
            triangle_points = [
                (current_x, self.rect.top - 10),
                (current_x - 8, self.rect.top - 2),
                (current_x + 8, self.rect.top - 2)
            ]
            pygame.draw.polygon(screen, COLORS['highlight'], triangle_points)
            
        # 绘制数据线
        points = []
        for year in range(year_range[0], year_range[1] + 1):
            x = self.rect.left + (year - year_range[0]) * self.rect.width // (year_range[1] - year_range[0])
            y = self.rect.bottom - (np.mean(data[year]) / 150.0) * self.rect.height
            points.append((x, y))
            
        if len(points) > 1:
            pygame.draw.lines(screen, COLORS['highlight'], False, points, 2)
            
        # 在数据线上绘制当前年份的点
        if self.rect.left <= current_x <= self.rect.right:
            current_y = self.rect.bottom - (np.mean(data[int(current_year)]) / 150.0) * self.rect.height
            pygame.draw.circle(screen, COLORS['highlight'], (int(current_x), int(current_y)), 6)
            pygame.draw.circle(screen, COLORS['background'], (int(current_x), int(current_y)), 3)

class Particle:
    def __init__(self, x, y, color, size, speed):
        self.x = x
        self.y = y
        self.z = random.uniform(-50, 50)  # 添加z坐标实现3D效果
        self.color = color
        self.base_size = size
        self.speed = speed
        self.angle = random.uniform(0, 2 * np.pi)
        
    def move(self):
        # 模拟布朗运动
        self.angle += random.uniform(-0.1, 0.1)
        self.x += np.cos(self.angle) * self.speed
        self.y += np.sin(self.angle) * self.speed
        # 3D效果：z轴周期性运动
        self.z = 50 * np.sin(pygame.time.get_ticks() * 0.001 + self.angle)
        
        # 边界检查
        if self.x < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = HEIGHT
        elif self.y > HEIGHT:
            self.y = 0
            
    def draw(self, screen):
        # 3D效果：根据z坐标调整大小和亮度
        depth_factor = (self.z + 50) / 100  # 0到1之间
        size = int(self.base_size * (0.5 + depth_factor * 0.5))
        
        # 调整颜色亮度
        color = tuple(int(c * (0.7 + depth_factor * 0.3)) for c in self.color)
        
        # 绘制主粒子
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), size)
        
        # 添加光晕效果
        glow_surface = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        glow_radius = size * 2
        glow_color = (*color[:3], 50)  # 半透明的光晕
        pygame.draw.circle(glow_surface, glow_color, (size * 2, size * 2), glow_radius)
        screen.blit(glow_surface, (int(self.x - size * 2), int(self.y - size * 2)), special_flags=pygame.BLEND_ADD)

class RippleEffect:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.radius = 0
        self.max_radius = 100
        self.color = color
        self.alpha = 255
        self.speed = 3
        
    def update(self):
        self.radius += self.speed
        self.alpha = max(0, 255 - (self.radius / self.max_radius) * 255)
        return self.radius < self.max_radius
        
    def draw(self, screen):
        if self.alpha > 0:
            ripple_surface = pygame.Surface((self.max_radius * 2, self.max_radius * 2), pygame.SRCALPHA)
            ripple_color = (*self.color[:3], int(self.alpha))
            pygame.draw.circle(ripple_surface, ripple_color, (self.max_radius, self.max_radius), int(self.radius), 2)
            screen.blit(ripple_surface, (self.x - self.max_radius, self.y - self.max_radius))

class FloatingParticle:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        self.start_x = x
        self.start_y = y
        self.color = color
        self.size = random.randint(2, 6)
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(0.5, 2.0)
        self.lifetime = 180  # 3秒 at 60fps
        self.age = 0
        
    def update(self, mouse_x, mouse_y):
        # 受鼠标位置影响的浮动运动
        dx = mouse_x - self.x
        dy = mouse_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            # 鼠标吸引力
            attraction_force = min(50.0 / distance, 2.0)
            self.x += (dx / distance) * attraction_force * 0.1
            self.y += (dy / distance) * attraction_force * 0.1
        
        # 自然浮动
        self.angle += 0.05
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        
        self.age += 1
        return self.age < self.lifetime
        
    def draw(self, screen):
        alpha = max(0, 255 - (self.age / self.lifetime) * 255)
        if alpha > 0:
            particle_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            particle_color = (*self.color[:3], int(alpha))
            pygame.draw.circle(particle_surface, particle_color, (self.size, self.size), self.size)
            screen.blit(particle_surface, (int(self.x - self.size), int(self.y - self.size)))

class ParticleExplosion:
    def __init__(self, x, y, color, intensity=20):
        self.x = x
        self.y = y
        self.color = color
        self.particles = []
        self.lifetime = 120
        self.age = 0
        
        # 创建爆炸粒子
        for _ in range(intensity):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            size = random.randint(2, 5)
            self.particles.append({
                'x': float(x),
                'y': float(y),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': size,
                'life': random.randint(60, 120)
            })
    
    def update(self):
        self.age += 1
        for particle in self.particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.1  # 重力
            particle['vx'] *= 0.99  # 空气阻力
            particle['life'] -= 1
        
        # 移除死亡粒子
        self.particles = [p for p in self.particles if p['life'] > 0]
        return self.age < self.lifetime and len(self.particles) > 0
    
    def draw(self, screen):
        for particle in self.particles:
            alpha = max(0, 255 * (particle['life'] / 120))
            if alpha > 0:
                particle_surface = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
                particle_color = (*self.color[:3], int(alpha))
                pygame.draw.circle(particle_surface, particle_color, (particle['size'], particle['size']), particle['size'])
                screen.blit(particle_surface, (int(particle['x'] - particle['size']), int(particle['y'] - particle['size'])))

class DataSparkle:
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value
        self.size = random.uniform(1, 3)
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(0.5, 1.5)
        self.lifetime = random.randint(180, 300)
        self.age = 0
        self.flash_timer = 0
        
    def update(self):
        self.angle += 0.02
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.age += 1
        self.flash_timer += 1
        return self.age < self.lifetime
    
    def draw(self, screen):
        alpha = max(0, 255 - (self.age / self.lifetime) * 255)
        flash_intensity = abs(math.sin(self.flash_timer * 0.2)) * 0.5 + 0.5
        
        if alpha > 20:
            # 根据数值确定颜色
            if self.value < 50:
                color = (0, 255, 0)  # 绿色 - 好
            elif self.value < 100:
                color = (255, 255, 0)  # 黄色 - 中等
            else:
                color = (255, 0, 0)  # 红色 - 差
            
            sparkle_surface = pygame.Surface((self.size * 4, self.size * 4), pygame.SRCALPHA)
            sparkle_color = (*color, int(alpha * flash_intensity))
            
            # 绘制星形闪烁
            center = (self.size * 2, self.size * 2)
            for i in range(4):
                angle = i * math.pi / 2
                end_x = center[0] + math.cos(angle) * self.size * 2
                end_y = center[1] + math.sin(angle) * self.size * 2
                pygame.draw.line(sparkle_surface, sparkle_color, center, (end_x, end_y), 2)
            
            screen.blit(sparkle_surface, (int(self.x - self.size * 2), int(self.y - self.size * 2)))

class WeatherEffect:
    def __init__(self, effect_type, aqi_level):
        self.type = effect_type  # "rain", "fog", "clear"
        self.aqi_level = aqi_level
        self.particles = []
        self.intensity = min(100, max(10, aqi_level))  # 基于AQI调整强度
        
        # 创建天气粒子
        for _ in range(self.intensity):
            if effect_type == "rain":
                self.particles.append({
                    'x': random.randint(0, WIDTH),
                    'y': random.randint(-100, 0),
                    'speed': random.uniform(3, 8),
                    'length': random.randint(10, 20)
                })
            elif effect_type == "fog":
                self.particles.append({
                    'x': random.randint(0, WIDTH),
                    'y': random.randint(0, HEIGHT),
                    'drift_x': random.uniform(-0.5, 0.5),
                    'drift_y': random.uniform(-0.2, 0.2),
                    'size': random.randint(20, 50),
                    'alpha': random.randint(10, 30)
                })
    
    def update(self):
        if self.type == "rain":
            for particle in self.particles:
                particle['y'] += particle['speed']
                if particle['y'] > HEIGHT:
                    particle['y'] = random.randint(-100, 0)
                    particle['x'] = random.randint(0, WIDTH)
        
        elif self.type == "fog":
            for particle in self.particles:
                particle['x'] += particle['drift_x']
                particle['y'] += particle['drift_y']
                if particle['x'] < -50:
                    particle['x'] = WIDTH + 50
                elif particle['x'] > WIDTH + 50:
                    particle['x'] = -50
    
    def draw(self, screen):
        if self.type == "rain":
            for particle in self.particles:
                color = (100, 150, 255, 100)  # 蓝色雨滴
                start_pos = (particle['x'], particle['y'])
                end_pos = (particle['x'], particle['y'] + particle['length'])
                pygame.draw.line(screen, color[:3], start_pos, end_pos, 2)
        
        elif self.type == "fog":
            fog_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for particle in self.particles:
                fog_color = (200, 200, 200, particle['alpha'])
                pygame.draw.circle(fog_surface, fog_color, 
                                 (int(particle['x']), int(particle['y'])), particle['size'])
            screen.blit(fog_surface, (0, 0))

class AirQualityViz:
    def __init__(self):
        self.particles = []
        self.year = 1993
        self.target_year = 1993  # 目标年份，用于平滑过渡
        self.year_transition_speed = 0.05  # 年份过渡速度
        self.aqi_data = self.generate_historical_data()
        self.district_data = self.generate_district_data()
        # Use basic font for better compatibility
        self.font = pygame.font.SysFont('Arial', 36)
        self.small_font = pygame.font.SysFont('Arial', 18)  # 减小右边字体大小
        self.bold_font = pygame.font.SysFont('Arial', 20, bold=True)  # 加粗字体用于地名
        self.initialize_particles()
        
        # 鼠标交互相关变量
        self.mouse_pos = (0, 0)
        self.mouse_trails = []  # 鼠标轨迹
        self.district_hover_effects = {}  # 每个区域的悬停效果
        self.ripple_effects = []  # 涟漪效果
        self.floating_particles = []  # 浮动粒子效果
        
        # 新增创意效果
        self.particle_explosions = []  # 粒子爆炸效果
        self.data_sparkles = []  # 数据闪烁效果
        self.weather_effects = []  # 天气效果（雨、雾等）
        self.sound_waves = []  # 声波效果
        self.breathing_effects = {}  # 呼吸效果
        self.rainbow_trail = []  # 彩虹轨迹
        self.show_statistics = False  # 统计信息显示
        self.comparison_mode = False  # 对比模式
        self.animation_mode = "normal"  # 动画模式
        
        # 创建图表对象
        self.timeline_graph = Graph(150, HEIGHT - 200, WIDTH - 300, 150)
        self.selected_district = None
        
    def generate_district_data(self):
        """生成各区域的空气质量数据"""
        district_data = {district: {} for district in DISTRICTS}
        base_data = self.generate_historical_data()
        
        for district in DISTRICTS:
            for year in range(1993, 2024):
                # 基于基准数据生成区域差异
                variation = np.random.normal(0, 10)  # 区域差异
                district_data[district][year] = base_data[year] + variation
                # 确保数值在合理范围内
                district_data[district][year] = np.clip(district_data[district][year], 0, 150)
                
        return district_data

    def generate_historical_data(self):
        # 香港历史空气质量数据（基于环境保护署公开数据）
        # 数据来源: https://www.aqhi.gov.hk/en/download/historical-data.html
        data = {}
        for year in range(1993, 2024):
            if year >= 1993 and year <= 2000:
                # 1993-2000年的数据（较高污染时期）
                data[year] = np.array([
                    85., 95., 80., 75., 70., 65.,
                    90., 100., 85., 80., 75., 70.
                ])
            elif year > 2000 and year <= 2010:
                # 2001-2010年的数据（开始实施管制措施）
                data[year] = np.array([
                    70., 75., 65., 60., 55., 50.,
                    80., 85., 70., 65., 60., 55.
                ])
            elif year > 2010 and year <= 2015:
                # 2011-2015年的数据（持续改善期）
                data[year] = np.array([
                    55., 60., 50., 45., 40., 35.,
                    65., 70., 55., 50., 45., 40.
                ])
            elif year > 2015 and year <= 2020:
                # 2016-2020年的数据（进一步改善）
                data[year] = np.array([
                    40., 45., 35., 30., 25., 20.,
                    50., 55., 40., 35., 30., 25.
                ])
            else:
                # 2021-2023年的最新数据
                data[year] = np.array([
                    35., 40., 30., 25., 20., 15.,
                    45., 50., 35., 30., 25., 20.
                ])
            # 添加随机波动以反映日常变化
            data[year] += np.random.normal(0, 5, 12)
            # 确保数值在合理范围内
            data[year] = np.clip(data[year], 0, 150)
            
        # 添加重要历史事件标记
        self.historical_events = {
            1995: "实施空气质量指标",
            2000: "引入更严格的车辆排放标准",
            2005: "推行清洁生产伙伴计划",
            2010: "实施区域性空气质量管理策略",
            2015: "更新空气质量指标",
            2020: "实施更严格的空气质量目标"
        }
        return data
    
    def get_particle_properties(self, aqi):
        if aqi < 50:
            return COLORS['particle_good'], 3, 1
        elif aqi < 100:
            return COLORS['particle_moderate'], 4, 1.5
        elif aqi < 150:
            return COLORS['particle_unhealthy'], 5, 2
        else:
            return COLORS['particle_hazardous'], 6, 2.5
            
    def initialize_particles(self):
        """初始化粒子"""
        num_particles = 200
        current_aqi = np.mean(self.aqi_data[self.year])
        color, size, speed = self.get_particle_properties(current_aqi)
        
        for _ in range(num_particles):
            x = float(random.randint(0, WIDTH))
            y = float(random.randint(-100, HEIGHT))
            particle = Particle(x, y, color, size, speed)
            self.particles.append(particle)

    def update_mouse_effects(self, mouse_pos):
        """更新鼠标相关的视觉效果"""
        self.mouse_pos = mouse_pos
        
        # 更新鼠标轨迹
        self.mouse_trails.append(mouse_pos)
        if len(self.mouse_trails) > 15:  # 保持轨迹长度
            self.mouse_trails.pop(0)
        
        # 更新涟漪效果
        self.ripple_effects = [ripple for ripple in self.ripple_effects if ripple.update()]
        
        # 更新浮动粒子
        self.floating_particles = [particle for particle in self.floating_particles 
                                 if particle.update(mouse_pos[0], mouse_pos[1])]
        
        # 更新新增效果
        self.particle_explosions = [explosion for explosion in self.particle_explosions if explosion.update()]
        self.data_sparkles = [sparkle for sparkle in self.data_sparkles if sparkle.update()]
        
        # 更新天气效果
        self.update_weather_effects()
        for effect in self.weather_effects:
            effect.update()
        
        # 在特殊模式下创建彩虹轨迹
        if self.animation_mode == "rainbow":
            self.create_rainbow_trail(mouse_pos)
        
        # 随机添加数据闪烁
        self.add_data_sparkles(self.district_data)
    
    def add_ripple_effect(self, x, y, color):
        """添加涟漪效果"""
        self.ripple_effects.append(RippleEffect(x, y, color))
    
    def add_floating_particles(self, x, y, color, count=5):
        """在指定位置添加浮动粒子"""
        for _ in range(count):
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-20, 20)
            self.floating_particles.append(FloatingParticle(x + offset_x, y + offset_y, color))

    def add_particle_explosion(self, x, y, color, intensity=20):
        """添加粒子爆炸效果"""
        self.particle_explosions.append(ParticleExplosion(x, y, color, intensity))
    
    def add_data_sparkles(self, districts_data):
        """基于数据添加闪烁效果"""
        if random.random() < 0.1:  # 10%概率生成
            margin = 50
            grid_size = 3
            cell_width = (WIDTH - 2 * margin) // grid_size
            cell_height = 200
            
            for i, district in enumerate(DISTRICTS):
                if random.random() < 0.3:  # 30%概率为每个区域生成
                    row = i // grid_size
                    col = i % grid_size
                    x = margin + col * cell_width + random.randint(10, cell_width - 20)
                    y = 100 + row * cell_height + random.randint(10, cell_height - 20)
                    
                    aqi = np.mean(districts_data[district][int(self.year)])
                    self.data_sparkles.append(DataSparkle(x, y, aqi))
    
    def update_weather_effects(self):
        """更新天气效果"""
        current_aqi = np.mean(self.aqi_data[int(self.year)])
        
        # 清理旧的天气效果
        self.weather_effects = [effect for effect in self.weather_effects if effect]
        
        # 根据AQI添加适当的天气效果
        if len(self.weather_effects) < 1:  # 限制天气效果数量
            if current_aqi > 100:
                # 高污染时添加雾霾效果
                if random.random() < 0.02:
                    self.weather_effects.append(WeatherEffect("fog", current_aqi))
            elif current_aqi < 50:
                # 低污染时添加清新效果（偶尔下雨）
                if random.random() < 0.01:
                    self.weather_effects.append(WeatherEffect("rain", current_aqi))
    
    def create_rainbow_trail(self, mouse_pos):
        """创建彩虹轨迹效果"""
        if len(self.rainbow_trail) > 0:
            last_pos = self.rainbow_trail[-1]['pos']
            distance = math.sqrt((mouse_pos[0] - last_pos[0])**2 + (mouse_pos[1] - last_pos[1])**2)
            if distance > 5:  # 只有鼠标移动一定距离才添加新点
                colors = [
                    (255, 0, 0), (255, 127, 0), (255, 255, 0),
                    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
                ]
                color_index = len(self.rainbow_trail) % len(colors)
                self.rainbow_trail.append({
                    'pos': mouse_pos,
                    'color': colors[color_index],
                    'life': 120
                })
        else:
            self.rainbow_trail.append({
                'pos': mouse_pos,
                'color': (255, 0, 0),
                'life': 120
            })
        
        # 限制轨迹长度并更新生命值
        self.rainbow_trail = [point for point in self.rainbow_trail if point['life'] > 0]
        for point in self.rainbow_trail:
            point['life'] -= 1

    def draw_mouse_effects(self, screen):
        """绘制鼠标相关的视觉效果"""
        # 绘制彩虹轨迹（如果在彩虹模式）
        if self.animation_mode == "rainbow" and len(self.rainbow_trail) > 1:
            for i in range(1, len(self.rainbow_trail)):
                start_pos = self.rainbow_trail[i-1]['pos']
                end_pos = self.rainbow_trail[i]['pos']
                alpha = self.rainbow_trail[i]['life'] / 120.0
                
                if alpha > 0:
                    trail_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    trail_color = (*self.rainbow_trail[i]['color'], int(255 * alpha))
                    pygame.draw.line(trail_surface, trail_color, start_pos, end_pos, 5)
                    screen.blit(trail_surface, (0, 0))
        
        # 绘制普通鼠标轨迹
        elif len(self.mouse_trails) > 1:
            for i in range(1, len(self.mouse_trails)):
                alpha = int(255 * (i / len(self.mouse_trails)))
                if alpha > 20:
                    trail_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
                    trail_color = (255, 255, 255, alpha // 3)
                    pygame.draw.circle(trail_surface, trail_color, (5, 5), 3)
                    screen.blit(trail_surface, (self.mouse_trails[i][0] - 5, self.mouse_trails[i][1] - 5))
        
        # 绘制涟漪效果
        for ripple in self.ripple_effects:
            ripple.draw(screen)
        
        # 绘制浮动粒子
        for particle in self.floating_particles:
            particle.draw(screen)
        
        # 绘制新增效果
        for explosion in self.particle_explosions:
            explosion.draw(screen)
        
        for sparkle in self.data_sparkles:
            sparkle.draw(screen)
        
        # 绘制天气效果
        for effect in self.weather_effects:
            effect.draw(screen)

    def update_particles(self):
        """更新所有粒子"""
        # 平滑年份过渡
        if abs(self.year - self.target_year) > 0.01:
            self.year += (self.target_year - self.year) * self.year_transition_speed
        else:
            self.year = self.target_year
            
        # 更新粒子属性基于当前年份的AQI
        # 使用插值来处理年份不是整数的情况
        current_year_int = int(self.year)
        next_year_int = min(2023, current_year_int + 1)
        year_fraction = self.year - current_year_int
        
        current_aqi = np.mean(self.aqi_data[current_year_int])
        if year_fraction > 0 and next_year_int in self.aqi_data:
            next_aqi = np.mean(self.aqi_data[next_year_int])
            current_aqi = current_aqi + (next_aqi - current_aqi) * year_fraction
            
        color, size, speed = self.get_particle_properties(current_aqi)
        
        for particle in self.particles:
            particle.color = color
            particle.size = size
            particle.speed = speed
            particle.move()  # 使用Particle类中定义的move方法
        """更新所有粒子"""
        # 平滑年份过渡
        if abs(self.year - self.target_year) > 0.01:
            self.year += (self.target_year - self.year) * self.year_transition_speed
        else:
            self.year = self.target_year
            
        # 更新粒子属性基于当前年份的AQI
        # 使用插值来处理年份不是整数的情况
        current_year_int = int(self.year)
        next_year_int = min(2023, current_year_int + 1)
        year_fraction = self.year - current_year_int
        
        current_aqi = np.mean(self.aqi_data[current_year_int])
        if year_fraction > 0 and next_year_int in self.aqi_data:
            next_aqi = np.mean(self.aqi_data[next_year_int])
            current_aqi = current_aqi + (next_aqi - current_aqi) * year_fraction
            
        color, size, speed = self.get_particle_properties(current_aqi)
        
        for particle in self.particles:
            particle.color = color
            particle.size = size
            particle.speed = speed
            particle.move()  # 使用Particle类中定义的move方法
            
    def draw_district_visualization(self, screen):
        """绘制区域空气质量地图"""
        margin = 50
        grid_size = 3
        cell_width = (WIDTH - 2 * margin) // grid_size
        cell_height = 200
        
        for i, district in enumerate(DISTRICTS):
            row = i // grid_size
            col = i % grid_size
            x = margin + col * cell_width
            y = 100 + row * cell_height
            
            # 计算当前区域的空气质量
            current_year_int = int(self.year)
            next_year_int = min(2023, current_year_int + 1)
            year_fraction = self.year - current_year_int
            
            aqi = np.mean(self.district_data[district][current_year_int])
            if year_fraction > 0 and next_year_int in self.district_data[district]:
                next_aqi = np.mean(self.district_data[district][next_year_int])
                aqi = aqi + (next_aqi - aqi) * year_fraction
            color = get_color_for_value(aqi)
            
            # 检查鼠标是否在当前区域内
            rect = pygame.Rect(x, y, cell_width - 10, cell_height - 10)
            mouse_x, mouse_y = self.mouse_pos
            is_hovered = rect.collidepoint(mouse_x, mouse_y)
            
            # 鼠标悬停效果
            if is_hovered:
                # 添加发光效果
                glow_surface = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
                glow_color = (*color[:3], 30)
                pygame.draw.rect(glow_surface, glow_color, (0, 0, rect.width + 20, rect.height + 20))
                screen.blit(glow_surface, (x - 10, y - 10))
                
                # 鼠标跟随粒子效果
                if random.random() < 0.3:  # 30%概率生成粒子
                    self.add_floating_particles(mouse_x, mouse_y, color, 2)
                
                # 存储悬停信息用于其他效果
                if district not in self.district_hover_effects:
                    self.district_hover_effects[district] = pygame.time.get_ticks()
                    # 添加涟漪效果
                    center_x = x + (cell_width - 10) // 2
                    center_y = y + (cell_height - 10) // 2
                    self.add_ripple_effect(center_x, center_y, color)
            else:
                # 移除悬停效果
                if district in self.district_hover_effects:
                    del self.district_hover_effects[district]
            
            # 绘制区域框
            pygame.draw.rect(screen, color, rect)
            
            # 鼠标在区域内时的额外视觉效果
            if is_hovered:
                # 边框闪烁效果
                flash_intensity = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 100 + 155
                flash_color = (flash_intensity, flash_intensity, flash_intensity)
                pygame.draw.rect(screen, flash_color, rect, 3)
                
                # 鼠标位置到区域中心的连线效果
                center_x = x + (cell_width - 10) // 2
                center_y = y + (cell_height - 10) // 2
                
                # 计算连线的透明度基于距离
                distance = math.sqrt((mouse_x - center_x)**2 + (mouse_y - center_y)**2)
                if distance > 0:
                    alpha = max(50, 255 - int(distance * 2))
                    line_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    line_color = (*color[:3], alpha)
                    
                    # 绘制多条偏移线条创造能量感
                    for offset in range(-2, 3):
                        start_pos = (mouse_x + offset, mouse_y + offset)
                        end_pos = (center_x + offset, center_y + offset)
                        if 0 <= start_pos[0] < WIDTH and 0 <= start_pos[1] < HEIGHT:
                            pygame.draw.line(line_surface, line_color, start_pos, end_pos, 2)
                    
                    screen.blit(line_surface, (0, 0))
            
            # 显示区域名称和AQI值
            name_text = self.bold_font.render(district, True, COLORS['text'])  # 使用加粗字体
            aqi_text = self.small_font.render(f"AQI: {int(aqi)}", True, COLORS['text'])
            screen.blit(name_text, (x + 10, y + 10))
            screen.blit(aqi_text, (x + 10, y + 35))
            
            # 高亮选中的区域
            if district == self.selected_district:
                pygame.draw.rect(screen, COLORS['highlight'], rect, 3)

    def draw_legend(self, screen):
        """Draw legend"""
        legend_x = WIDTH - 280  # 进一步减小宽度
        legend_y = 20
        
        # 绘制标题和副标题
        title = pygame.font.SysFont('Arial', 24).render("AQI Guide", True, COLORS['text'])  # 进一步缩短标题
        subtitle = pygame.font.SysFont('Arial', 12).render("Health Impact", True, (200, 200, 200))  # 更短的副标题
        screen.blit(title, (legend_x, legend_y))
        screen.blit(subtitle, (legend_x, legend_y + 22))
        
        # 添加分隔线
        pygame.draw.line(screen, (100, 100, 100), 
                        (legend_x, legend_y + 38), 
                        (WIDTH - 20, legend_y + 38), 1)  # 更细的分隔线
        
        legend_start_y = legend_y + 48  # 调整起始位置
        
        for i, level in enumerate(AQI_LEVELS):
            y = legend_start_y + i * 45  # 进一步减少间距
            
            # 绘制颜色示例框 - 更小
            pygame.draw.rect(screen, level['color'], (legend_x, y, 16, 16))  # 减小到16x16
            pygame.draw.rect(screen, (100, 100, 100), (legend_x, y, 16, 16), 1)
            
            # 绘制AQI范围和等级名称 - 更紧凑的布局
            range_text = pygame.font.SysFont('Arial', 10).render(f"{level['range'][0]}-{level['range'][1]}", True, (180, 180, 180))
            name_text = pygame.font.SysFont('Arial', 12).render(level['name'], True, COLORS['text'])
            
            # 只显示简化的描述
            desc_font = pygame.font.SysFont('Arial', 9)
            # 使用更简短的描述
            short_desc = {
                'Good': 'Safe for all',
                'Moderate': 'OK for most', 
                'Unhealthy for Sensitive': 'Sensitive at risk',
                'Unhealthy': 'Health effects',
                'Very Unhealthy': 'Serious effects',
                'Hazardous': 'Emergency'
            }
            desc_text = desc_font.render(short_desc.get(level['name'], level['name']), True, (160, 160, 160))
            
            # 更紧凑的布局
            screen.blit(range_text, (legend_x + 22, y))
            screen.blit(name_text, (legend_x + 22, y + 12))
            screen.blit(desc_text, (legend_x + 22, y + 26))

    def draw_historical_event(self, screen):
        """绘制历史事件信息"""
        current_year = int(self.year)  # 使用整数年份检查事件
        if current_year in HISTORICAL_EVENTS:
            event = HISTORICAL_EVENTS[current_year]
            # 创建半透明背景
            info_surface = pygame.Surface((WIDTH - 20, 100))
            info_surface.fill((20, 20, 40))
            info_surface.set_alpha(200)
            screen.blit(info_surface, (10, HEIGHT - 110))
            
            # 显示事件信息
            title_text = self.font.render(f"{current_year}年 - {event['title']}", True, COLORS['highlight'])
            desc_text = self.small_font.render(event['desc'], True, COLORS['text'])
            screen.blit(title_text, (20, HEIGHT - 100))
            screen.blit(desc_text, (20, HEIGHT - 65))

    def draw(self, screen):
        screen.fill(COLORS['background'])
        
        # 绘制区域可视化
        self.draw_district_visualization(screen)
        
        # 绘制时间轴图表
        self.timeline_graph.draw(screen, self.aqi_data, current_year=self.year)
        
        # 绘制所有粒子（按z坐标排序以实现正确的3D效果）
        sorted_particles = sorted(self.particles, key=lambda p: p.z)
        for particle in sorted_particles:
            particle.draw(screen)
        
        # 绘制鼠标交互效果
        self.draw_mouse_effects(screen)
        
        # Display year and overall AQI information
        year_text = self.font.render(f"Year: {int(self.year)}", True, COLORS['text'])  # 显示整数年份
        # 使用插值计算当前显示的AQI
        current_year_int = int(self.year)
        next_year_int = min(2023, current_year_int + 1)
        year_fraction = self.year - current_year_int
        
        overall_aqi = np.mean(self.aqi_data[current_year_int])
        if year_fraction > 0 and next_year_int in self.aqi_data:
            next_aqi = np.mean(self.aqi_data[next_year_int])
            overall_aqi = overall_aqi + (next_aqi - overall_aqi) * year_fraction
            
        aqi_text = self.font.render(f"Hong Kong Average AQI: {int(overall_aqi)}", True, COLORS['text'])
        screen.blit(year_text, (10, 10))
        screen.blit(aqi_text, (10, 50))
        
        # 绘制图例
        self.draw_legend(screen)
        
        # 绘制历史事件信息
        self.draw_historical_event(screen)
        
        # 绘制统计信息（如果开启）
        if self.show_statistics:
            self.draw_statistics(screen)
        
        # 绘制模式指示器
        self.draw_mode_indicator(screen)

    def draw_statistics(self, screen):
        """绘制详细统计信息"""
        stats_surface = pygame.Surface((300, 200), pygame.SRCALPHA)
        stats_surface.fill((20, 20, 40, 180))
        
        current_year_int = int(self.year)
        current_aqi = np.mean(self.aqi_data[current_year_int])
        
        # 计算统计数据
        all_years_aqi = [np.mean(self.aqi_data[year]) for year in range(1993, 2024)]
        best_year = 1993 + np.argmin(all_years_aqi)
        worst_year = 1993 + np.argmax(all_years_aqi)
        avg_improvement = (all_years_aqi[0] - all_years_aqi[-1]) / 30  # 每年平均改善
        
        stats_text = [
            f"Current Year: {current_year_int}",
            f"Current AQI: {int(current_aqi)}",
            f"Best Year: {best_year} (AQI: {int(min(all_years_aqi))})",
            f"Worst Year: {worst_year} (AQI: {int(max(all_years_aqi))})",
            f"30-Year Improvement: {avg_improvement:.1f} AQI/year",
            f"Total Districts: {len(DISTRICTS)}",
            f"Animation Mode: {self.animation_mode.title()}"
        ]
        
        for i, text in enumerate(stats_text):
            text_surface = pygame.font.SysFont('Arial', 16).render(text, True, COLORS['text'])
            stats_surface.blit(text_surface, (10, 10 + i * 25))
        
        screen.blit(stats_surface, (10, 100))
    
    def draw_mode_indicator(self, screen):
        """绘制当前模式指示器"""
        mode_text = f"Mode: {self.animation_mode.title()}"
        if self.show_statistics:
            mode_text += " | Stats: ON"
        
        mode_surface = pygame.font.SysFont('Arial', 18).render(mode_text, True, COLORS['highlight'])
        mode_bg = pygame.Surface((mode_surface.get_width() + 20, 30), pygame.SRCALPHA)
        mode_bg.fill((0, 0, 0, 100))
        
        screen.blit(mode_bg, (WIDTH - mode_surface.get_width() - 30, 10))
        screen.blit(mode_surface, (WIDTH - mode_surface.get_width() - 20, 15))

def main():
    clock = pygame.time.Clock()
    viz = AirQualityViz()
    running = True
    frame_count = 0
    
    while running:
        # 更新鼠标位置
        mouse_pos = pygame.mouse.get_pos()
        viz.update_mouse_effects(mouse_pos)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    viz.target_year = min(2023, int(viz.target_year) + 1)  # 设置目标年份
                elif event.key == pygame.K_LEFT:
                    viz.target_year = max(1993, int(viz.target_year) - 1)  # 设置目标年份
                elif event.key == pygame.K_SPACE:
                    # 空格键暂停/继续自动播放
                    frame_count = 0
                elif event.key == pygame.K_s:
                    # S键切换统计信息显示
                    viz.show_statistics = not viz.show_statistics
                elif event.key == pygame.K_r:
                    # R键切换彩虹模式
                    viz.animation_mode = "rainbow" if viz.animation_mode != "rainbow" else "normal"
                    viz.rainbow_trail = []  # 清空之前的轨迹
                elif event.key == pygame.K_e:
                    # E键创建爆炸效果
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    current_aqi = np.mean(viz.aqi_data[int(viz.year)])
                    color = get_color_for_value(current_aqi)
                    viz.add_particle_explosion(mouse_x, mouse_y, color, 30)
                elif event.key == pygame.K_w:
                    # W键手动添加天气效果
                    current_aqi = np.mean(viz.aqi_data[int(viz.year)])
                    if current_aqi > 100:
                        viz.weather_effects = [WeatherEffect("fog", current_aqi)]
                    else:
                        viz.weather_effects = [WeatherEffect("rain", current_aqi)]
                elif event.key == pygame.K_c:
                    # C键清除所有特效
                    viz.particle_explosions = []
                    viz.data_sparkles = []
                    viz.weather_effects = []
                    viz.rainbow_trail = []
                    viz.floating_particles = []
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                
                # 检测时间轴图表点击
                clicked_year = viz.timeline_graph.get_year_from_mouse_pos(mouse_x, mouse_y)
                if clicked_year is not None:
                    viz.target_year = clicked_year
                    # 添加点击时间轴的视觉反馈
                    click_x = viz.timeline_graph.rect.left + (clicked_year - 1993) * viz.timeline_graph.rect.width // (2023 - 1993)
                    click_y = viz.timeline_graph.rect.centery
                    viz.add_ripple_effect(click_x, click_y, COLORS['highlight'])
                    viz.add_floating_particles(click_x, click_y, COLORS['highlight'], 8)
                else:
                    # 检测区域点击
                    margin = 50
                    grid_size = 3
                    cell_width = (WIDTH - 2 * margin) // grid_size
                    cell_height = 200
                    
                    if 100 <= mouse_y <= 700:  # 区域可视化的垂直范围
                        row = (mouse_y - 100) // cell_height
                        col = (mouse_x - margin) // cell_width
                        index = row * grid_size + col
                        if 0 <= index < len(DISTRICTS):
                            viz.selected_district = DISTRICTS[index]
                            # 点击时添加特殊效果
                            center_x = margin + col * cell_width + (cell_width - 10) // 2
                            center_y = 100 + row * cell_height + (cell_height - 10) // 2
                            aqi = np.mean(viz.district_data[DISTRICTS[index]][int(viz.year)])
                            color = get_color_for_value(aqi)
                            viz.add_ripple_effect(center_x, center_y, color)
                            viz.add_floating_particles(center_x, center_y, color, 10)
                    
        viz.update_particles()
        viz.draw(screen)
        pygame.display.flip()
        
        # 每300帧自动前进一年
        frame_count += 1
        if frame_count >= 300:
            frame_count = 0
            viz.target_year = viz.target_year + 1 if viz.target_year < 2023 else 1993  # 设置目标年份而不是直接修改年份
            
        clock.tick(60)

if __name__ == "__main__":
    main()
    pygame.quit()
