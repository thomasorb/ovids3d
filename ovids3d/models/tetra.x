xof 0303txt 0032

Frame Root {
  FrameTransformMatrix {
     1.000000, 0.000000, 0.000000, 0.000000,
     0.000000,-0.000000, 1.000000, 0.000000,
     0.000000, 1.000000, 0.000000, 0.000000,
     0.000000, 0.000000, 0.000000, 1.000000;;
  }
  Frame Cone {
    FrameTransformMatrix {
       1.000000, 0.000000, 0.000000, 0.000000,
       0.000000, 1.000000, 0.000000, 0.000000,
       0.000000, 0.000000, 1.000000, 0.000000,
       1.000018,-0.815084, 0.897635, 1.000000;;
    }
    Mesh { // Cone mesh
      4;
       0.000000; 1.000000;-0.500000;,
       0.866025;-0.500000;-0.500000;,
      -0.866025;-0.500000;-0.500000;,
       0.000000; 0.000000; 0.500000;;
      4;
      3;1,3,0;,
      3;2,3,1;,
      3;0,3,2;,
      3;2,1,0;;
      MeshNormals { // Cone normals
        4;
         0.774597; 0.447214; 0.447214;,
        -0.000000;-0.894427; 0.447214;,
        -0.774597; 0.447214; 0.447214;,
         0.000000; 0.000000;-1.000000;;
        4;
        3;0,0,0;,
        3;1,1,1;,
        3;2,2,2;,
        3;3,3,3;;
      } // End of Cone normals
    } // End of Cone mesh
  } // End of Cone
} // End of Root
