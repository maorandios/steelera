"use client";

import { useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

import {
  VIEWPORT_PICK_ROLE,
  viewportPickTargetFromHits,
} from "@/lib/viewport-pick";
import { useProjectStore } from "@/store/project-store";

const PICK_MOVE_THRESHOLD_PX = 10;

/**
 * Reliable click-to-select that does not compete with OrbitControls drag.
 * A quick tap raycasts all hits (skipping grid lines) and picks the member;
 * drag only orbits.
 */
export function ViewportPointerPicker() {
  const { camera, gl, scene } = useThree();
  const selectElement = useProjectStore((state) => state.selectElement);
  const clearSelection = useProjectStore((state) => state.clearSelection);
  const raycaster = useMemo(() => {
    const caster = new THREE.Raycaster();
    caster.params.Line.threshold = 0.02;
    return caster;
  }, []);
  const pointer = useMemo(() => new THREE.Vector2(), []);
  const pointerDownRef = useRef<{
    x: number;
    y: number;
    pendingPick: boolean;
  } | null>(null);

  useEffect(() => {
    const raycastHits = (clientX: number, clientY: number) => {
      const rect = gl.domElement.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) {
        return [];
      }
      pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      return raycaster.intersectObjects(scene.children, true);
    };

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) {
        return;
      }
      pointerDownRef.current = {
        x: event.clientX,
        y: event.clientY,
        pendingPick: true,
      };
    };

    const onPointerMove = (event: PointerEvent) => {
      const down = pointerDownRef.current;
      if (!down?.pendingPick) {
        return;
      }
      const dx = event.clientX - down.x;
      const dy = event.clientY - down.y;
      if (dx * dx + dy * dy > PICK_MOVE_THRESHOLD_PX * PICK_MOVE_THRESHOLD_PX) {
        down.pendingPick = false;
      }
    };

    const onPointerUp = (event: PointerEvent) => {
      if (event.button !== 0) {
        return;
      }
      const down = pointerDownRef.current;
      pointerDownRef.current = null;
      if (!down?.pendingPick) {
        return;
      }

      const hits = raycastHits(down.x, down.y);
      const target = viewportPickTargetFromHits(hits);
      if (target?.type === VIEWPORT_PICK_ROLE.ELEMENT) {
        selectElement(target.elementId);
        return;
      }
      if (target?.type === VIEWPORT_PICK_ROLE.BACKGROUND) {
        clearSelection();
        return;
      }
      clearSelection();
    };

    const canvas = gl.domElement;
    canvas.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    return () => {
      canvas.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [camera, clearSelection, gl, pointer, raycaster, scene, selectElement]);

  return null;
}
