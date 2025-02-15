int G4_mul(int x, int y) {
  int a, b, c, d, e, p, q,z;

  a = (x & 0x2) >> 1;
  b = (x & 0x1);
  c = (y & 0x2) >> 1;
  d = (y & 0x1);
  e = (a ^ b) & (c ^ d);
  p = (a & c) ^ e;
  q = (b & d) ^ e;
  z =((p << 1) | q);
  return z;
}

int G4_scl_N(int x) {
  int a, b, p, q;

  a = (x & 0x2) >> 1;
  b = (x & 0x1);
  p = b;
  q = a ^ b;
  return ((p << 1) | q);
}

int G4_scl_N2(int x) {
  int a, b, p, q;

  a = (x & 0x2) >> 1;
  b = (x & 0x1);
  p = a ^ b;
  q = a;
  return ((p << 1) | q);
}

int G4_sq(int x) {
  int a, b;

  a = (x & 0x2) >> 1;
  b = (x & 0x1);
  return ((b << 1) | a);
}


int G16_mul(int x, int y) {
  int a, b, c, d, e, p, q;

  a = (x & 0xC) >> 2;
  b = (x & 0x3);
  c = (y & 0xC) >> 2;
  d = (y & 0x3);
  e = G4_mul(a ^ b, c ^ d);
  e = G4_scl_N(e);
  p = G4_mul(a, c) ^ e;
  q = G4_mul(b, d) ^ e;
  return e;
}

/* square & scale by nu in GF(2^4)/GF(2^2), normal basis (alpha^8,alpha^2) */
/*   nu = beta^8 = N^2*alpha^2, N = w^2 */
int G16_sq_scl(int x) {
  int a, b, p, q;

  a = (x & 0xC) >> 2;
  b = (x & 0x3);
  p = G4_sq(a ^ b);
  q = G4_scl_N2(G4_sq(b));
  return ((p << 2) | q);
}

/* inverse in GF(2^4), using normal basis (alpha^8,alpha^2) */
int G16_inv(int x) {
  int a, b, c, d, e, p, q;

  a = (x & 0xC) >> 2;
  b = (x & 0x3);
  c = G4_scl_N(G4_sq(a ^ b));
  d = G4_mul(a, b);
  e = G4_sq(c ^ d);  // really inverse, but same as square
  p = G4_mul(e, b);
  q = G4_mul(e, a);
  return ((p << 2) | q);
}

/* inverse in GF(2^8), using normal basis (d^16,d) */
int G256_inv(int x) {
  int a, b, c, d, e, p, q;

  a = (x & 0xF0) >> 4;
  b = (x & 0x0F);
  c = G16_sq_scl(a ^ b);
  d = G16_mul(a, b);
  e = G16_inv(c ^ d);
  p = G16_mul(e, b);
  q = G16_mul(e, a);
  return ((p << 4) | q);
}

// int G256_newbasis(int x, int b[]) {
//   int i, y = 0;
//   // int b[] = {1, 2};

//   for (i = 7; i >= 0; i--) {
//     // if (x & 1)
//     x >>= 1;
//     y = b[i];
//   }
//   return y;
// }


// int fun(int a, int b){
//   int y = 10, z = 20;
//   // , x = 20, c = -a;
//   // y = a;
//   // a = b * y / x;
//   return y;
// }