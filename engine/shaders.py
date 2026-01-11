# Standard Blit
DEFAULT_VERT = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 uv;
void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
    uv = in_uv;
}
"""

DEFAULT_FRAG = """
#version 330
in vec2 uv;
out vec4 fragColor;
uniform sampler2D tex;
void main() {
    fragColor = texture(tex, uv);
}
"""

# Glitch / Broken Screen Effect
GLITCH_FRAG = """
#version 330
in vec2 uv;
out vec4 fragColor;
uniform sampler2D tex;
uniform float time;
uniform float intensity;

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main() {
    vec2 t_uv = uv;
    
    if (intensity > 0.01) {
        float block_size = 0.05 + (0.1 * (1.0 - intensity)); 
        vec2 block = floor(uv / block_size);
        float r = rand(block + floor(time * 10.0));
        
        if (r < intensity * 0.3) {
            float disp = (rand(block) - 0.5) * intensity * 0.5;
            t_uv.x += disp;
        }
    }

    float r_off = intensity * 0.02;
    float b_off = -intensity * 0.02;
    
    float r = texture(tex, t_uv + vec2(r_off, 0.0)).r;
    float g = texture(tex, t_uv).g;
    float b = texture(tex, t_uv + vec2(b_off, 0.0)).b;
    float a = texture(tex, t_uv).a;
    
    if (intensity > 0.5) {
        float scan = sin(uv.y * 800.0) * 0.1;
        r -= scan; g -= scan; b -= scan;
    }

    fragColor = vec4(r, g, b, a);
}
"""

# CRT Effect
CRT_FRAG = """
#version 330
in vec2 uv;
out vec4 fragColor;
uniform sampler2D tex;

void main() {
    vec2 p = uv * 2.0 - 1.0;
    vec2 offset = p * dot(p, p) * 0.1;
    p += offset;
    
    if (abs(p.x) > 1.0 || abs(p.y) > 1.0) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }
    
    vec2 tc = (p + 1.0) * 0.5;
    vec4 color = texture(tex, tc);
    
    float scan = sin(tc.y * 600.0) * 0.1 + 0.9;
    color.rgb *= scan;
    
    float vig = 1.0 - dot(p, p) * 0.2;
    color.rgb *= vig;
    
    fragColor = color;
}
"""

# VHS + Cracking Effect
VHS_FRAG = """
#version 330
in vec2 uv;
out vec4 fragColor;
uniform sampler2D tex;
uniform float time;
uniform float intensity; // 0.0 to 1.0 (Low to High Corruption)

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 ip = floor(p);
    vec2 u = fract(p);
    u = u*u*(3.0-2.0*u);
    
    float res = mix(
        mix(rand(ip), rand(ip+vec2(1.0,0.0)), u.x),
        mix(rand(ip+vec2(0.0,1.0)), rand(ip+vec2(1.0,1.0)), u.x),
        u.y);
    return res*res;
}

void main() {
    vec2 t_uv = uv;
    
    // 1. VHS Wobbly Distortion (Always present but scales)
    float wave = sin(0.3 * time + t_uv.y * 21.0) * 0.002 * (1.0 + intensity * 5.0);
    t_uv.x += wave;

    // 2. Heavy Cracking / Block Displacement (High Intensity)
    if (intensity > 0.3) {
        float block_size = 0.1;
        vec2 block = floor(t_uv * 10.0); // Large blocks
        float n = rand(block + floor(time * 15.0));
        
        // Randomly offset blocks
        if (n < (intensity - 0.2) * 0.4) {
             t_uv.x += (rand(block) - 0.5) * 0.1 * intensity;
             t_uv.y += (rand(block + 1.0) - 0.5) * 0.05 * intensity;
        }
    }
    
    // 3. Color Bleed / Aberration
    float offset = 0.002 + 0.02 * intensity;
    float r = texture(tex, t_uv + vec2(offset, 0.0)).r;
    float g = texture(tex, t_uv).g;
    float b = texture(tex, t_uv - vec2(offset, 0.0)).b;
    float a = texture(tex, t_uv).a;
    
    // 4. Static Noise / Grain
    float grain = rand(uv + time) * 0.15 * intensity;
    vec3 col = vec3(r, g, b) + grain;
    
    // 5. Desaturation at high intensity (Screen looking dead)
    if (intensity > 0.6) {
        vec3 gray = vec3(dot(col, vec3(0.299, 0.587, 0.114)));
        col = mix(col, gray, (intensity - 0.6) * 2.0);
    }
    
    fragColor = vec4(col, a);
}
"""

# Matrix / Row-Shifting Effect
MATRIX_FRAG = """
#version 330
in vec2 uv;
out vec4 fragColor;
uniform sampler2D tex;
uniform float time;
uniform float intensity;

void main() {
    if (intensity < 0.05) {
        fragColor = texture(tex, uv);
        return;
    }

    float lines = 12.0;
    float line_id = floor(uv.y * lines);
    
    // Different speed and direction for each line
    float speed = (fract(line_id * 0.456) - 0.5) * 2.0;
    float offset = sin(time * speed + line_id) * 0.05 * intensity;
    
    vec2 t_uv = uv;
    t_uv.x += offset;
    
    // Subtle chromatic aberration on the edges of the lines
    float r = texture(tex, t_uv + vec2(0.002 * intensity, 0.0)).r;
    float g = texture(tex, t_uv).g;
    float b = texture(tex, t_uv - vec2(0.002 * intensity, 0.0)).b;
    float a = texture(tex, t_uv).a;
    
    vec3 col = vec3(r, g, b);
    
    // Matrix-y green tint
    vec3 green_tint = vec3(0.8, 1.2, 0.8);
    col *= mix(vec3(1.0), green_tint, intensity * 0.4);
    
    fragColor = vec4(col, a);
}
"""
