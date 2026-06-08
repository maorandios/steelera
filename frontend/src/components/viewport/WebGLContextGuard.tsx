"use client";

import { useThree } from "@react-three/fiber";
import { useEffect } from "react";

type WebGLContextGuardProps = {
  onLost: () => void;
  onRestored: () => void;
};

/** Listens for WebGL context loss/restoration with proper cleanup on remount. */
export function WebGLContextGuard({ onLost, onRestored }: WebGLContextGuardProps) {
  const gl = useThree((state) => state.gl);

  useEffect(() => {
    const canvas = gl.domElement;
    const handleLost = (event: Event) => {
      event.preventDefault();
      onLost();
    };
    const handleRestored = () => {
      gl.resetState();
      onRestored();
    };
    canvas.addEventListener("webglcontextlost", handleLost);
    canvas.addEventListener("webglcontextrestored", handleRestored);
    return () => {
      canvas.removeEventListener("webglcontextlost", handleLost);
      canvas.removeEventListener("webglcontextrestored", handleRestored);
    };
  }, [gl, onLost, onRestored]);

  return null;
}
