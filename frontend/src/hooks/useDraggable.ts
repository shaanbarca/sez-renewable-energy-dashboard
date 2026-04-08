import { useCallback, useRef, useState } from 'react';

interface Position {
  x: number;
  y: number;
}

export function useDraggable(initialPos: Position = { x: 0, y: 0 }) {
  const [position, setPosition] = useState<Position>(initialPos);
  const dragging = useRef(false);
  const offset = useRef<Position>({ x: 0, y: 0 });

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      offset.current = { x: e.clientX - position.x, y: e.clientY - position.y };

      const onMove = (ev: MouseEvent) => {
        if (dragging.current) {
          setPosition({
            x: ev.clientX - offset.current.x,
            y: ev.clientY - offset.current.y,
          });
        }
      };

      const onUp = () => {
        dragging.current = false;
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    },
    [position],
  );

  return { position, handleMouseDown };
}
