# faz o setup do ambiente
import sys
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLU import *
from OpenGL.GLUT import *

import glfw
import math
import numpy as np


PI = 3.14

# shaders
vertex_shader = '''
#version 330

in vec3 position;
in vec3 normal;
in vec2 TexCoord;

uniform mat4 projection, modelview, normalMat;

out vec3 normalInterp;
out vec3 vertPos;
out vec4 vertexColor; //only for gouraud

const vec3 lightPos = vec3(2.0, 1.0, 1.0);
const vec3 ambientColor = vec3(0.0, 0.1, 0.1);
const vec3 diffuseColor = vec3(0.0, 0.6, 0.6);
const vec3 specularColor = vec3(1.0, 1.0, 1.0);

uniform float Ka;   // Ambient reflection coefficient
uniform float Kd;   // Diffuse reflection coefficient
uniform float Ks;   // Specular reflection coefficient
uniform float shininessVal; // Shininess


void main(){
    gl_Position = projection * modelview * vec4(position, 1.0);

    normalInterp = vec3(normalMat * vec4(normal, 0.0));

    // ------------ only for gouraud -----------------
    vec3 normal = vec3(normalMat * vec4(normal, 0.0));
    vec4 vertPos4 = modelview * vec4(position, 1.0);
    vertPos = vec3(vertPos4) / vertPos4.w;
    vec3 lightDir = normalize(lightPos - vertPos);
    vec3 reflectDir = reflect(-lightDir, normal);
    vec3 viewDir = normalize(-vertPos);

    float lambertian = max(dot(lightDir,normal), 0.0);
    float specular = 0.0;

    if(lambertian > 0.0) {
       float specAngle = max(dot(reflectDir, viewDir), 0.0);
       specular = pow(specAngle, 4.0);
    }

    vertexColor = vec4(ambientColor+lambertian*diffuseColor + specular*specularColor, 1.0);

}

'''

fragment_shader = '''
#version 330

precision mediump float;

in vec3 normalInterp;  // Surface normal
in vec3 vertPos;       // Vertex position
in vec4 vertexColor;  // Only for gouraud

const vec3 lightPos = vec3(2.0,1.0,1.0);
const vec3 ambientColor = vec3(0.0, 0.1, 0.1);
const vec3 diffuseColor = vec3(0.0, 0.6, 0.6);
const vec3 specularColor = vec3(1.0, 1.0, 1.0);

uniform int shading;

uniform float Ka;   // Ambient reflection coefficient
uniform float Kd;   // Diffuse reflection coefficient
uniform float Ks;   // Specular reflection coefficient
uniform float shininessVal; // Shininess 

out vec4 color;

void main(){    
    //flat
    if(shading == 0) {
        vec3 normal = normalize(normalInterp);
        vec3 lightDir = normalize(lightPos - vertPos);
        vec3 reflectDir = reflect(-lightDir, normal);
        vec3 viewDir = normalize(-vertPos);

        float lambertian = max(dot(lightDir,normal), 0.0);
        float specular = 0.0;

        if(lambertian > 0.0) {
        float specAngle = max(dot(reflectDir, viewDir), 0.0);
        specular = pow(specAngle, 4.0);
        }

        color = vec4(ambientColor +
                      lambertian*diffuseColor +
                      specular*specularColor, 1.0);

    }
    // gouraud
    else if(shading == 1) {
        color = vertexColor;
    }
    // phong
    else {  
        vec3 normal = normalize(normalInterp);
        vec3 lightDir = normalize(lightPos - vertPos);
        vec3 reflectDir = reflect(-lightDir, normal);
        vec3 viewDir = normalize(-vertPos);

        //lightDir*normal
        float lambertian = max(dot(lightDir,normal), 0.0);
        float specular = 0.0;

        if(lambertian > 0.0) {
        float specAngle = max(dot(reflectDir, viewDir), 0.0);
        specular = pow(specAngle, 4.0);
        }
        color = vec4(ambientColor +
                        lambertian*diffuseColor +
                        specular*specularColor, 1.0);


    }
}
'''

  
class Shape:
    def __init__(self, shape, shader):
        self.shape = shape
        self.shader = shader

    def render(self):
        qobj = gluNewQuadric()
        gluQuadricNormals(qobj, GLU_SMOOTH)
        gluQuadricOrientation(qobj, GLU_OUTSIDE)
        vn = glGetAttribLocation(self.shader, 'normal')
        glVertexAttrib3f(vn, 0.0, 0.0, 0.0)
        glDisableVertexAttribArray(vn)

        if self.shape == 'sphere':
            gluSphere(qobj, 1, 50, 50)
        elif self.shape == 'cylinder':
            gluCylinder(qobj, 1, 1, 1, 50, 50)
        else:
            glutSolidTeapot(50.0)


class Renderer:
    def __init__(self):
        self.t = 0.0
        self.modeVal = 0
        self.lightPos = [1.0, 1.0, -1.0]
        self.lightVec = np.array([0, 0, 0], dtype="float32")
        self.ambientColor = [0.2, 0.1, 0.0]
        self.diffuseColor = [0.8, 0.4, 0.0]
        self.specularColor = [1.0, 1.0, 1.0]
        self.clearColor = [0.0, 0.4, 0.7]
        self.attenuation = 0.01
        self.shininess = 80.0
        self.kaVal = 1.0
        self.kdVal = 1.0
        self.ksVal = 1.0
       
        self.sceneVertNo = 0
        self.progID = 0
        self.vertID = 0
        self.fragID = 0
        self.vertexLoc = 0
        self.texCoordLoc = 0
        self.normalLoc = 0
        self.projectionLoc = 0
        self.modelviewLoc = 0
        self.normalMatrixLoc = 0
        self.modeLoc = 0
        self.kaLoc = 0
        self.kdLoc = 0
        self.ksLoc = 0
        self.attenuationLoc = 0
        self.shininessLoc = 0
        self.lightPosLoc = 0
        self.lightVecLoc = 0
        self.ambientColorLoc = 0
        self.diffuseColorLoc = 0
        self.specularColorLoc = 0
        self.projection = np.zeros((16,), dtype="float32")  # projection matrix
        self.modelview = np.zeros((16,), dtype="float32")   # modelview matrix

    def start(self, shader, shape):
        glEnable(GL_DEPTH_TEST)
        self.setupShaders(shader, shape)
        

    def setupShaders(self, shader, s):
        glUseProgram(shader)
    
        # retrieve the location of the IN variables of the vertex shaders
        vertexLoc = glGetAttribLocation(shader,"position")
        texCoordLoc = glGetAttribLocation(shader,"TexCoord")
        normalLoc = glGetAttribLocation(shader, "normal")

        # retrieve the location of the UNIFORM variables of the shader
        projectionLoc = glGetUniformLocation(shader, "projection")
        modelviewLoc = glGetUniformLocation(shader, "modelview")
        normalMatrixLoc = glGetUniformLocation(shader, "normalMat")
        # lightPosLoc = glGetUniformLocation(shader, "lightPos")
        # ambientColorLoc = glGetUniformLocation(shader, "ambientColor")
        # diffuseColorLoc = glGetUniformLocation(shader, "diffuseColor")
        # specularColorLoc = glGetUniformLocation(shader, "specularColor")
        
        shading = glGetUniformLocation(shader, 'shading')
        if s == 'flat':
            glUniform1i(shading, 0)
        elif s == 'gouraud':
            glUniform1i(shading, 1)
        else:
            glUniform1i(shading, 2)

    def display(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        rad = PI / 180.0 * self.t
    
        self.mat4LookAt(self.modelview,
               1.5*float(math.cos(rad)), 1.5*float(math.sin(rad)), 1.5, # eye
               0.0, 0.0, 0.0, # look at
               0.0, 0.0, 1.0) # up


        modelviewInv = np.zeros((16,), dtype="float32")
        normalmatrix = np.zeros((16,), dtype="float32")
        self.mat4Invert(self.modelview, modelviewInv)
        self.mat4Transpose(modelviewInv, normalmatrix)
        
        # load the current projection and modelview matrix into the
        # corresponding UNIFORM variables of the shader
        glUniformMatrix4fv(self.projectionLoc, 1, GL_FALSE, self.projection)
        glUniformMatrix4fv(self.modelviewLoc, 1, GL_FALSE, self.modelview)
        if(self.normalMatrixLoc != -1):
            glUniformMatrix4fv(self.normalMatrixLoc, 1, GL_FALSE, normalmatrix)
       


    
    # ----- the following functions are some matrix and vector helpers --------
    def vec3Dot(self, a, b):
        return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

    def vec3Cross(self, a, b, res):
        res[0] = a[1] * b[2]  -  b[1] * a[2]
        res[1] = a[2] * b[0]  -  b[2] * a[0]
        res[2] = a[0] * b[1]  -  b[0] * a[1]


    def vec3Normalize(self, a):
        mag = math.sqrt(a[0] * a[0]  +  a[1] * a[1]  +  a[2] * a[2])
        a[0] /= mag; a[1] /= mag; a[2] /= mag
  

    def mat4Identity(self, a):
        for i in range(16):
            a[i] = 0.0
        for i in range(4):
            a[i + i * 4] = 1.0
    
    def mat4Multiply(a, b, res):
        for i in range(4):
            for j in range(4): 
                res[j*4 + i] = 0.0
                for k in range(4): 
                    res[j*4 + i] += a[k*4 + i] * b[j*4 + k]

    
    def mat4Perspective(self, a, fov, aspect, zNear, zFar):
        f = 1.0 / (math.tan (fov/2.0 * (PI / 180.0)))
        self.mat4Identity(a)
        a[0] = f / aspect
        a[1 * 4 + 1] = f
        a[2 * 4 + 2] = (zFar + zNear)  / (zNear - zFar)
        a[3 * 4 + 2] = (2.0 * zFar * zNear) / (zNear - zFar)
        a[2 * 4 + 3] = -1.0
        a[3 * 4 + 3] = 0.0
    

    def mat4LookAt(self,viewMatrix,
                    eyeX, eyeY, eyeZ,
                    centerX, centerY, centerZ,
                    upX, upY, upZ):

        dr = np.zeros((3,), dtype="float32")
        right = np.zeros((3,), dtype="float32")
        up = np.zeros((3,), dtype="float32")
        eye = np.zeros((3,), dtype="float32")

        up[0]=upX
        up[1]=upY 
        up[2]=upZ

        eye[0]=eyeX
        eye[1]=eyeY
        eye[2]=eyeZ

        dr[0]=centerX-eyeX
        dr[1]=centerY-eyeY
        dr[2]=centerZ-eyeZ

        self.vec3Normalize(dr)
        self.vec3Cross(dr,up,right)
        self.vec3Normalize(right)
        self.vec3Cross(right,dr,up)
        self.vec3Normalize(up)

        # first row
        viewMatrix[0]  = right[0]
        viewMatrix[4]  = right[1]
        viewMatrix[8]  = right[2]
        viewMatrix[12] = -self.vec3Dot(right, eye)

        # second row
        viewMatrix[1]  = up[0]
        viewMatrix[5]  = up[1]
        viewMatrix[9]  = up[2]
        viewMatrix[13] = -self.vec3Dot(up, eye)
        
        # third row
        viewMatrix[2]  = -dr[0]
        viewMatrix[6]  = -dr[1]
        viewMatrix[10] = -dr[2]
        viewMatrix[14] =  self.vec3Dot(dr, eye)

        # forth row
        viewMatrix[3]  = 0.0
        viewMatrix[7]  = 0.0
        viewMatrix[11] = 0.0
        viewMatrix[15] = 1.0
    

    def mat4Print(self, a):
        # opengl uses column major order
        for i in range(4):
            for i in range(4): 
                print(a[j * 4 + i] + " ")
            print("\n")
        

    def mat4Transpose(self,a, transposed):
        t = 0
        for i in range(4):
            for j in range(4): 
                transposed[t] = a[j * 4 + i]
                t +=1
        

    def mat4Invert(self,m, inverse):
        inv = np.zeros((16,), dtype="float32")
        inv[0] = m[5]*m[10]*m[15]-m[5]*m[11]*m[14]-m[9]*m[6]*m[15]+m[9]*m[7]*m[14]+m[13]*m[6]*m[11]-m[13]*m[7]*m[10]
        inv[4] = -m[4]*m[10]*m[15]+m[4]*m[11]*m[14]+m[8]*m[6]*m[15]-m[8]*m[7]*m[14]-m[12]*m[6]*m[11]+m[12]*m[7]*m[10]
        inv[8] = m[4]*m[9]*m[15]-m[4]*m[11]*m[13]-m[8]*m[5]*m[15]+m[8]*m[7]*m[13]+m[12]*m[5]*m[11]-m[12]*m[7]*m[9]
        inv[12]= -m[4]*m[9]*m[14]+m[4]*m[10]*m[13]+m[8]*m[5]*m[14]-m[8]*m[6]*m[13]-m[12]*m[5]*m[10]+m[12]*m[6]*m[9]
        inv[1] = -m[1]*m[10]*m[15]+m[1]*m[11]*m[14]+m[9]*m[2]*m[15]-m[9]*m[3]*m[14]-m[13]*m[2]*m[11]+m[13]*m[3]*m[10]
        inv[5] = m[0]*m[10]*m[15]-m[0]*m[11]*m[14]-m[8]*m[2]*m[15]+m[8]*m[3]*m[14]+m[12]*m[2]*m[11]-m[12]*m[3]*m[10]
        inv[9] = -m[0]*m[9]*m[15]+m[0]*m[11]*m[13]+m[8]*m[1]*m[15]-m[8]*m[3]*m[13]-m[12]*m[1]*m[11]+m[12]*m[3]*m[9]
        inv[13]= m[0]*m[9]*m[14]-m[0]*m[10]*m[13]-m[8]*m[1]*m[14]+m[8]*m[2]*m[13]+m[12]*m[1]*m[10]-m[12]*m[2]*m[9]
        inv[2] = m[1]*m[6]*m[15]-m[1]*m[7]*m[14]-m[5]*m[2]*m[15]+m[5]*m[3]*m[14]+m[13]*m[2]*m[7]-m[13]*m[3]*m[6]
        inv[6] = -m[0]*m[6]*m[15]+m[0]*m[7]*m[14]+m[4]*m[2]*m[15]-m[4]*m[3]*m[14]-m[12]*m[2]*m[7]+m[12]*m[3]*m[6]
        inv[10]= m[0]*m[5]*m[15]-m[0]*m[7]*m[13]-m[4]*m[1]*m[15]+m[4]*m[3]*m[13]+m[12]*m[1]*m[7]-m[12]*m[3]*m[5]
        inv[14]= -m[0]*m[5]*m[14]+m[0]*m[6]*m[13]+m[4]*m[1]*m[14]-m[4]*m[2]*m[13]-m[12]*m[1]*m[6]+m[12]*m[2]*m[5]
        inv[3] = -m[1]*m[6]*m[11]+m[1]*m[7]*m[10]+m[5]*m[2]*m[11]-m[5]*m[3]*m[10]-m[9]*m[2]*m[7]+m[9]*m[3]*m[6]
        inv[7] = m[0]*m[6]*m[11]-m[0]*m[7]*m[10]-m[4]*m[2]*m[11]+m[4]*m[3]*m[10]+m[8]*m[2]*m[7]-m[8]*m[3]*m[6]
        inv[11]= -m[0]*m[5]*m[11]+m[0]*m[7]*m[9]+m[4]*m[1]*m[11]-m[4]*m[3]*m[9]-m[8]*m[1]*m[7]+m[8]*m[3]*m[5]
        inv[15]= m[0]*m[5]*m[10]-m[0]*m[6]*m[9]-m[4]*m[1]*m[10]+m[4]*m[2]*m[9]+m[8]*m[1]*m[6]-m[8]*m[2]*m[5]

        det = m[0]*inv[0]+m[1]*inv[4]+m[2]*inv[8]+m[3]*inv[12]
        if (det == 0):
             return False
        det = 1.0 / det
        for i in range(16):
            inverse[i] = inv[i] * det
        return True

renderer = Renderer()

def glutDisplay():
  renderer.display()
  glutSwapBuffers()
  glutReportErrors()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DEPTH | GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowPosition(300,40)
    glutInitWindowSize(700, 700)

    window = glutCreateWindow("Shading")
    glutDisplayFunc(glutDisplay)
    # glutFullScreen()

    glutIdleFunc(glutDisplay)
    # glutReshapeFunc(glutResize)
    # glutKeyboardFunc(glutKeyboard)

    # compile the shader
    shader = shaders.compileProgram(shaders.compileShader(vertex_shader, GL_VERTEX_SHADER), shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER))
    shape = Shape('sphere', shader)

    renderer = Renderer()
    renderer.start(shader, 'sphere')
    shape.render()
    glutDisplay()

    glutMainLoop()


if __name__ == '__main__':
    main()