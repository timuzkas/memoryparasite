DEFAULT_VERT = """
#version 330
in vec2 in_pos; in vec2 in_uv; out vec2 uv;
void main() { gl_Position = vec4(in_pos, 0.0, 1.0); uv = in_uv; }
"""

DEFAULT_FRAG = """
#version 330
in vec2 uv; out vec4 fragColor; uniform sampler2D tex;
void main() { fragColor = texture(tex, uv); }
"""

GLITCH_FRAG = """
#version 330
in vec2 uv; out vec4 fragColor; uniform sampler2D tex; uniform float time; uniform float intensity;
float rand(vec2 co){ return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453); }
void main() {
    vec2 t_uv = uv;
    if (intensity > 0.01) {
        float b_sz = 0.05 + (0.1 * (1.0 - intensity)); vec2 block = floor(uv / b_sz);
        if (rand(block + floor(time * 10.0)) < intensity * 0.3) t_uv.x += (rand(block) - 0.5) * intensity * 0.5;
    }
    float r = texture(tex, t_uv + vec2(intensity * 0.02, 0.0)).r;
    float g = texture(tex, t_uv).g;
    float b = texture(tex, t_uv - vec2(intensity * 0.02, 0.0)).b;
    if (intensity > 0.5) { float scan = sin(uv.y * 800.0) * 0.1; r -= scan; g -= scan; b -= scan; }
    fragColor = vec4(r, g, b, texture(tex, t_uv).a);
}
"""

CRT_FRAG = """
#version 330
in vec2 uv; out vec4 fragColor; uniform sampler2D tex;
void main() {
    vec2 p = uv * 2.0 - 1.0; p += p * dot(p, p) * 0.1;
    if (abs(p.x) > 1.0 || abs(p.y) > 1.0) { fragColor = vec4(0,0,0,1); return; }
    vec2 tc = (p + 1.0) * 0.5; vec4 col = texture(tex, tc);
    col.rgb *= (sin(tc.y * 600.0) * 0.1 + 0.9) * (1.0 - dot(p, p) * 0.2);
    fragColor = col;
}
"""

VHS_FRAG = """
#version 330
in vec2 uv; out vec4 fragColor; uniform sampler2D tex; uniform float time; uniform float intensity;
float rand(vec2 co){ return fract(sin(dot(co.xy, vec2(12.9898,78.233))) * 43758.5453); }
void main() {
    vec2 t_uv = uv; t_uv.x += sin(0.3 * time + t_uv.y * 21.0) * 0.002 * (1.0 + intensity * 5.0);
    if (intensity > 0.3) {
        vec2 block = floor(t_uv * 10.0);
        if (rand(block + floor(time * 15.0)) < (intensity - 0.2) * 0.4) t_uv += (rand(block) - 0.5) * 0.1 * intensity;
    }
    float off = 0.002 + 0.02 * intensity;
    vec3 col = vec3(texture(tex, t_uv + vec2(off, 0.0)).r, texture(tex, t_uv).g, texture(tex, t_uv - vec2(off, 0.0)).b) + rand(uv + time) * 0.15 * intensity;
    if (intensity > 0.6) col = mix(col, vec3(dot(col, vec3(0.299, 0.587, 0.114))), (intensity - 0.6) * 2.0);
    fragColor = vec4(col, texture(tex, t_uv).a);
}
"""

MATRIX_FRAG = """
#version 330
in vec2 uv; out vec4 fragColor; uniform sampler2D tex; uniform float time; uniform float intensity;
void main() {
    if (intensity < 0.05) { fragColor = texture(tex, uv); return; }
    float l_id = floor(uv.y * 12.0);
    vec2 t_uv = uv; t_uv.x += sin(time * (fract(l_id * 0.456) - 0.5) * 2.0 + l_id) * 0.05 * intensity;
    float off = 0.002 * intensity;
    vec3 col = vec3(texture(tex, t_uv + vec2(off, 0.0)).r, texture(tex, t_uv).g, texture(tex, t_uv - vec2(off, 0.0)).b);
    fragColor = vec4(col * mix(vec3(1.0), vec3(0.8, 1.2, 0.8), intensity * 0.4), texture(tex, t_uv).a);
}
"""