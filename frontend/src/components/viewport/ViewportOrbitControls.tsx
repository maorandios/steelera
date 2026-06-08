"use client";

import { OrbitControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

type ViewportOrbitControlsProps = {
  /** Recentres orbit pivot when structural bounds shift (e.g. after generate). */
  defaultTarget: [number, number, number];
};

function moveOrbitTargetWithoutJump(
  controls: OrbitControlsImpl,
  camera: THREE.Camera,
  next: THREE.Vector3,
) {
  const delta = next.clone().sub(controls.target);
  controls.target.copy(next);
  camera.position.add(delta);
  controls.update();
}

/**
 * Snappy orbit (no damping). Selection does not move the camera; zoom pulls
 * toward the cursor so orbit stays local after zooming in.
 */
export function ViewportOrbitControls({
  defaultTarget,
}: ViewportOrbitControlsProps) {
  const { camera } = useThree();
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const defaultKey = defaultTarget.map((v) => v.toFixed(3)).join(",");

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) {
      return;
    }
    moveOrbitTargetWithoutJump(
      controls,
      camera,
      new THREE.Vector3(defaultTarget[0], defaultTarget[1], defaultTarget[2]),
    );
  }, [defaultKey, defaultTarget, camera]);

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping={false}
      enablePan
      enableZoom
      enableRotate
      zoomToCursor
      rotateSpeed={1.85}
      zoomSpeed={1.15}
      panSpeed={1.2}
      screenSpacePanning
      mouseButtons={{
        LEFT: THREE.MOUSE.ROTATE,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.PAN,
      }}
    />
  );
}
