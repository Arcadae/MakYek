import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Optional, Tuple, Set, Any, TypeAlias, TypedDict, Literal
import hashlib
import json
import os
import copy
from BotClass import BotPlayer

CELL_SIZE: int = 80
BOARD_SIZE: int = 8
BOARD_COLOR_LIGHT: str = "#FFFFFF"
BOARD_COLOR_DARK: str = "#000000"
WHITE_PIECE_COLOR: str = "#FFFFFF"
RED_PIECE_COLOR: str = "#FF0000"
HIGHLIGHT_COLOR: str = "#00FF00"
CROWN_COLOR: str = "#FFD700"

Position: TypeAlias = Tuple[int, int]
PieceColor: TypeAlias = Literal["WHITE", "RED"]

class PieceData(TypedDict, total=False):
    color: str
    piece: Any 
    is_king: bool
    crown: Optional[Any] 

class MakYek:
    def __init__(self, root: tk.Tk) -> None:
        self.game_over = False
        self.game_ended = False

        self.root = root
        self.root.title("Тайские шашки")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.game_mode = "vs_bot"
        self.player_color = "WHITE"  # Игрок всегда белые
        self.bot = BotPlayer(game_instance=self)
        self.bot_thinking = False

        bg_color = "#E0E0E0"
        self.root.configure(bg=bg_color)
        
        window_width = 1200
        window_height = 800
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.resizable(False, False)
        
        self.main_frame = tk.Frame(root, bg=bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.moves_frame = tk.Frame(self.main_frame, width=300, bg=bg_color)
        self.moves_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=20)
        
        self.moves_label = tk.Label(
            self.moves_frame,
            text="Журнал ходов",
            font=("Arial", 16, "bold"),
            bg=bg_color
        )
        self.moves_label.pack(pady=10)
        
        self.moves_text = tk.Text(
            self.moves_frame,
            width=35,
            height=35,
            font=("Arial", 12),
            bg="#F0F0F0"
        )
        self.moves_text.pack(pady=10)
        
        self.game_frame = tk.Frame(self.main_frame, bg=bg_color)
        self.game_frame.pack(side=tk.LEFT, padx=20, pady=20)
        
        self._create_menu()
        
        self.canvas = tk.Canvas(
            self.game_frame,
            width=CELL_SIZE * BOARD_SIZE,
            height=CELL_SIZE * BOARD_SIZE + 40
        )
        self.canvas.pack()
        
        self.moved_this_turn = False
        self._init_game()

    def _init_game(self) -> None:
        self.board: List[List[Optional[PieceData]]] = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.selected_piece: Optional[PieceData] = None
        self.start_pos: Optional[Position] = None
        self.valid_moves: Set[Position] = set()
        
        self.current_turn: PieceColor = "WHITE"
        self.current_player_text: str = "Белые"

        self.red_pieces: int = 8
        self.white_pieces: int = 8

        self.moved_this_turn = False
        self._init_board()
        self._place_pieces()
        
        self._create_labels()
        
        self._bind_events()

    def get_board_state(self) -> List[List[Optional[PieceData]]]:

        simplified_board = []
        for row in range(BOARD_SIZE):
            board_row = []
            for col in range(BOARD_SIZE):
                if self.board[row][col]:
                    piece = self.board[row][col]
                    board_row.append({
                        "color": piece["color"],
                        "is_king": piece["is_king"]
                    })
                else:
                    board_row.append(None)
            simplified_board.append(board_row)
        return simplified_board

    def _create_labels(self) -> None:
        if hasattr(self, 'labels_frame'):
            self.labels_frame.destroy()
            
        self.labels_frame = tk.Frame(self.game_frame, bg="#E0E0E0")
        self.labels_frame.pack(side=tk.TOP, pady=5)
            
        self.turn_label = tk.Label(
            self.labels_frame,
            text=f"Ходят {self.current_player_text}",
            font=("Arial", 16),
            bg="#E0E0E0"
        )
        self.turn_label.pack(side=tk.TOP)

        self.score_label = tk.Label(
            self.labels_frame,
            text=f"Красные: {self.red_pieces} | Белые: {self.white_pieces}",
            font=("Arial", 14),
            bg="#E0E0E0"
        )
        self.score_label.pack(side=tk.TOP)

    def _init_board(self) -> None:
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                color = BOARD_COLOR_LIGHT if (row + col) % 2 == 0 else BOARD_COLOR_DARK
                x1, y1 = col * CELL_SIZE, row * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def _place_pieces(self) -> None:
        for row in range(2):
            for col in range(BOARD_SIZE):
                if (row + col) % 2 == 1:
                    self._add_piece(row, col, RED_PIECE_COLOR)

        for row in range(BOARD_SIZE - 2, BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if (row + col) % 2 == 1:
                    self._add_piece(row, col, WHITE_PIECE_COLOR)

    def _add_piece(self, row: int, col: int, color: str) -> None:
        x, y = col * CELL_SIZE, row * CELL_SIZE
        piece = self.canvas.create_oval(
            x + 10, y + 10,
            x + CELL_SIZE - 10, y + CELL_SIZE - 10,
            fill=color, outline="black"
        )
        self.board[row][col] = {
            "color": color,
            "piece": piece,
            "is_king": False,
            "crown": None
        }

    def _bind_events(self) -> None:
        # Привязываем события только если не думает бот и это ход игрока (белые)
        if not self.bot_thinking and self.current_turn == "WHITE":
            self.canvas.bind("<ButtonPress-1>", self._on_piece_click)
            self.canvas.bind("<ButtonRelease-1>", self._on_drop)
        else:
            # Отвязываем события во время хода бота или когда не ход игрока
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<ButtonRelease-1>")

    def _on_piece_click(self, event: tk.Event) -> None:
        self._clear_highlights()
        col, row = event.x // CELL_SIZE, event.y // CELL_SIZE
        
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return

        piece = self.board[row][col]
        if piece and piece["color"]:
            if piece["is_king"] and self.moved_this_turn:
                return
            
            if ((self.current_turn == "RED" and piece["color"] == RED_PIECE_COLOR) or
                (self.current_turn == "WHITE" and piece["color"] == WHITE_PIECE_COLOR)):
                self.selected_piece = piece
                self.start_pos = (row, col)
                self._highlight_valid_moves(row, col)

    def _highlight_valid_moves(self, row: int, col: int) -> None:
        piece = self.board[row][col]
        self.valid_moves: Set[Position] = set()
        
        if self.moved_this_turn and piece["is_king"]:
            return
        
        all_captures = self._check_all_captures()
        
        if all_captures:
            if (row, col) in all_captures and not self.moved_this_turn:
                self._check_captures(row, col, [], set())
            return
        
        if not self.moved_this_turn:
            if piece["is_king"]:
                directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                for dr, dc in directions:
                    curr_row, curr_col = row + dr, col + dc
                    while 0 <= curr_row < BOARD_SIZE and 0 <= curr_col < BOARD_SIZE:
                        if self.board[curr_row][curr_col]:  # Если встретили фигуру
                            break
                        self.valid_moves.add((curr_row, curr_col))
                        self._highlight_cell(curr_row, curr_col)
                        curr_row += dr
                        curr_col += dc
            else:
                directions = [(-1, -1), (-1, 1)] if piece["color"] == WHITE_PIECE_COLOR else [(1, -1), (1, 1)]
                for dr, dc in directions:
                    new_row = row + dr
                    new_col = col + dc
                    if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and not self.board[new_row][new_col]:
                        self.valid_moves.add((new_row, new_col))
                        self._highlight_cell(new_row, new_col)

    def _check_all_captures(self) -> Set[Position]:
        captures: Set[Position] = set()
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece and piece["color"]:
                    if piece["is_king"] and self.moved_this_turn:
                        continue
                    
                    if (self.current_turn == "RED" and piece["color"] == RED_PIECE_COLOR) or \
                       (self.current_turn == "WHITE" and piece["color"] == WHITE_PIECE_COLOR):
                        if self._check_captures(row, col, [], set(), check_only=True):
                            captures.add((row, col))
        return captures

    def _check_captures(self, row: int, col: int, path: List[Position], 
                       visited: Set[Position], check_only: bool = False) -> bool:
        piece = self.board[row][col]
        if not piece:
            return False
        
        has_captures = False
        eaten_positions = set(path[i] for i in range(1, len(path), 2))
        
        if piece["is_king"]:
            # Для дамки - только одиночное взятие
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                curr_row, curr_col = row + dr, col + dc
                while 0 <= curr_row < BOARD_SIZE and 0 <= curr_col < BOARD_SIZE:
                    if (curr_row, curr_col) in eaten_positions:
                        break
                    
                    curr_piece = self.board[curr_row][curr_col]
                    if curr_piece:
                        if curr_piece["color"] != piece["color"]:
                            next_row, next_col = curr_row + dr, curr_col + dc
                            if 0 <= next_row < BOARD_SIZE and 0 <= next_col < BOARD_SIZE and not self.board[next_row][next_col]:
                                has_captures = True
                                if check_only:
                                    return True
                                
                                self.valid_moves.add((next_row, next_col))
                                self._highlight_cell(next_row, next_col)
                        break
                    curr_row += dr
                    curr_col += dc
        else:
            # Для шашки оставляем множественное взятие
            if piece["color"] == WHITE_PIECE_COLOR:
                directions = [(-2, -2), (-2, 2)]
            else:
                directions = [(2, -2), (2, 2)]
            
            for dr, dc in directions:
                capture_row, capture_col = row + dr, col + dc
                middle_row, middle_col = row + dr//2, col + dc//2
                
                if (capture_row, capture_col) not in visited and \
                   0 <= capture_row < BOARD_SIZE and 0 <= capture_col < BOARD_SIZE:
                    middle_piece = self.board[middle_row][middle_col]
                    if middle_piece and middle_piece["color"] != piece["color"] and \
                       (middle_row, middle_col) not in eaten_positions and \
                       not self.board[capture_row][capture_col]:
                        has_captures = True
                        if check_only:
                            return True
                        
                        new_path = path + [(capture_row, capture_col), (middle_row, middle_col)]
                        visited.add((capture_row, capture_col))
                        
                        next_captures = self._check_captures(capture_row, capture_col, new_path, visited)
                        
                        if not next_captures:
                            self.valid_moves.add((capture_row, capture_col))
                            self._highlight_cell(capture_row, capture_col)
        
        return has_captures

    def _highlight_cell(self, row: int, col: int) -> None:
        x1, y1 = col * CELL_SIZE, row * CELL_SIZE
        x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=HIGHLIGHT_COLOR, stipple="gray50", tags="highlight")

    def _clear_highlights(self) -> None:
        self.valid_moves: Set[Position] = set()
        self.canvas.delete("highlight")

    def _add_move_to_log(self, start_pos: Position, end_pos: Position, is_capture: bool = False) -> None:
        start_col, start_row = chr(start_pos[1] + 97), 8 - start_pos[0]
        end_col, end_row = chr(end_pos[1] + 97), 8 - end_pos[0]
        
        move_text = f"{self.current_player_text}: {start_col}{start_row}"
        move_text += " => "
        move_text += f"{end_col}{end_row}\n"
        
        self.moves_text.insert(tk.END, move_text)
        self.moves_text.see(tk.END)

    def _on_drop(self, event: tk.Event) -> None:
        if self.game_over:
            return

        if self.selected_piece:
            col: int = event.x // CELL_SIZE
            row: int = event.y // CELL_SIZE
            if (row, col) in self.valid_moves:
                old_row, old_col = self.start_pos
                is_capture: bool = False

                # Проверяем было ли взятие
                if abs(row - old_row) >= 2 or abs(col - old_col) >= 2:
                    is_capture = True
                    dr = 1 if row > old_row else -1
                    dc = 1 if col > old_col else -1
                    curr_row, curr_col = old_row, old_col
                    
                    while curr_row != row or curr_col != col:
                        curr_row += dr
                        curr_col += dc
                        if self.board[curr_row][curr_col]:
                            self._remove_piece(curr_row, curr_col)
                            break

                # Перемещаем шашку
                self.board[row][col] = self.board[old_row][old_col]
                self.board[old_row][old_col] = None
                self._update_piece_position(row, col)

                # Проверяем превращение в дамку для шашки
                if not self.selected_piece["is_king"] and \
                   ((row == 0 and self.selected_piece["color"] == WHITE_PIECE_COLOR) or \
                    (row == BOARD_SIZE - 1 and self.selected_piece["color"] == RED_PIECE_COLOR)):
                    self._make_king(row, col)
                    self._add_move_to_log((old_row, old_col), (row, col), is_capture)
                    self._change_turn()
                    self._clear_highlights()
                    self.selected_piece = None
                    self.start_pos = None
                    self.valid_moves.clear()
                    return

                if self.selected_piece["is_king"]:
                    self._add_move_to_log((old_row, old_col), (row, col), is_capture)
                    self.moved_this_turn = True
                    self._change_turn()
                    self._clear_highlights()
                    self.selected_piece = None
                    self.start_pos = None
                    self.valid_moves.clear()
                    return

                # Для шашки
                if not is_capture:
                    self._add_move_to_log((old_row, old_col), (row, col), is_capture)
                    self._change_turn()
                else:
                    self._add_move_to_log((old_row, old_col), (row, col), is_capture)
                    if self._check_captures(row, col, [], set()):
                        self.selected_piece = self.board[row][col]
                        self.start_pos = (row, col)
                        self._clear_highlights()
                        self._highlight_valid_moves(row, col)
                        return
                    self._change_turn()
                
                self._clear_highlights()
                self.selected_piece = None
                self.start_pos = None

    def _schedule_bot_move(self) -> None:
        if self.bot_thinking:
            return
        
        self.bot_thinking = True

        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<ButtonRelease-1>")
        
        self.root.after(800, self._make_bot_move)  
    
    def _make_bot_move(self) -> None:
        if self.game_over:  # ← ПРОВЕРКА
            self.bot_thinking = False
            return
        
        try:
            timeout_id = self.root.after(5_000, self._bot_timeout)
            move = self.bot.get_move()
            self.root.after_cancel(timeout_id)

            if move:
                start_pos, end_pos = move
                self._execute_bot_move(start_pos, end_pos)
            else:
                self._check_winner()
        finally:
            self.bot_thinking = False
            self._bind_events()

    def _bot_timeout(self):
        self.bot_thinking = False
        self._bind_events()
        messagebox.showwarning("Внимание", "Бот завис, ход переходит к вам")

    def _execute_bot_move(self, start_pos: Position, end_pos: Position) -> None:
        old_row, old_col = start_pos
        new_row, new_col = end_pos
        
        # Проверяем было ли взятие
        is_capture = abs(new_row - old_row) >= 2 or abs(new_col - old_col) >= 2
        
        if hasattr(self, 'bot') and hasattr(self.bot, 'learn_from_move'):
            before_state_hash = self.bot.get_state_hash(self.get_board_state())
            action_hash = self.bot.get_action_hash(start_pos, end_pos)

        # Удаляем срубленную фигуру если нужно
        if is_capture:
            dr = 1 if new_row > old_row else -1
            dc = 1 if new_col > old_col else -1
            curr_row, curr_col = old_row + dr, old_col + dc
            
            while curr_row != new_row or curr_col != new_col:
                if self.board[curr_row][curr_col]:
                    self._remove_piece(curr_row, curr_col)
                    break
                curr_row += dr
                curr_col += dc
        
        # Перемещаем фигуру
        piece = self.board[old_row][old_col]
        self.board[new_row][new_col] = piece
        self.board[old_row][old_col] = None
        
        # Обновляем позицию на canvas
        x, y = new_col * CELL_SIZE, new_row * CELL_SIZE
        self.canvas.coords(
            piece["piece"],
            x + 10, y + 10,
            x + CELL_SIZE - 10, y + CELL_SIZE - 10
        )
        
        if piece["crown"]:
            self.canvas.coords(
                piece["crown"],
                x + 25, y + 25,
                x + CELL_SIZE - 25, y + CELL_SIZE - 25
            )
        
        # Проверяем превращение в дамку
        became_king = False
        if not piece["is_king"]:
            if (new_row == 0 and piece["color"] == WHITE_PIECE_COLOR) or \
               (new_row == BOARD_SIZE - 1 and piece["color"] == RED_PIECE_COLOR):
                self._make_king(new_row, new_col)
                became_king = True
        
        if hasattr(self, 'bot') and hasattr(self.bot, 'learn_from_move'):
            if before_state_hash and action_hash:
                reward = self.bot.get_reward(
                    self.get_board_state(), 
                    True,           # move_made
                    is_capture,     # is_capture
                    is_capture,     # piece_captured (если было взятие)
                    became_king     # became_king
                )   
                self.bot.learn_from_move(
                    before_state_hash, 
                    action_hash, 
                    self.get_board_state(), 
                    reward
                )
        
        # Логируем ход
        self._add_move_to_log(start_pos, end_pos, is_capture)
        
        # Меняем ход
        self._change_turn()

    def _remove_piece(self, row: int, col: int) -> None:
        piece = self.board[row][col]
        if piece:
            self.canvas.delete(piece["piece"])
            if piece["crown"]:
                self.canvas.delete(piece["crown"])
            self.board[row][col] = None
            
            if piece["color"] == RED_PIECE_COLOR:
                self.red_pieces -= 1
            else:
                self.white_pieces -= 1
            
            self._update_score()
            self._check_winner()

    def _update_score(self) -> None:
        self.score_label.config(text=f"Красные: {self.red_pieces} | Белые: {self.white_pieces}")

    def _check_winner(self) -> None:
        if self.game_over:  # Проверка, не закончена ли уже игра
            return
        
        # Проверка на отсутствие шашек
        if self.red_pieces == 0:
            self._show_winner("белые")
            return
        elif self.white_pieces == 0:
            self._show_winner("красные")
            return

        # Проверка на пат
        current_color = RED_PIECE_COLOR if self.current_turn == "RED" else WHITE_PIECE_COLOR
        has_valid_moves = False

        # Сначала проверяем наличие обязательных взятий
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece and piece["color"] == current_color:
                    if self._check_captures(row, col, [], set(), check_only=True):
                        has_valid_moves = True
                        break
            if has_valid_moves:
                break

        # Если нет взятий, проверяем наличие обычных ходов
        if not has_valid_moves:
            for row in range(BOARD_SIZE):
                for col in range(BOARD_SIZE):
                    piece = self.board[row][col]
                    if piece and piece["color"] == current_color:
                        if piece["is_king"]:
                            # Проверка ходов для дамки
                            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                            for dr, dc in directions:
                                new_row, new_col = row + dr, col + dc
                                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                                    if not self.board[new_row][new_col]:
                                        has_valid_moves = True
                                        break
                        else:
                            # Проверка ходов для шашки
                            directions = [(-1, -1), (-1, 1)] if current_color == WHITE_PIECE_COLOR else [(1, -1), (1, 1)]
                            for dr, dc in directions:
                                new_row, new_col = row + dr, col + dc
                                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                                    if not self.board[new_row][new_col]:
                                        has_valid_moves = True
                                        break
                        if has_valid_moves:
                            break
                if has_valid_moves:
                    break

        if not has_valid_moves:
            self.game_over = True
            winner = "белые" if self.current_turn == "RED" else "красные"
            self._show_winner(f"{winner} (пат)")

    def _show_winner(self, winner: str) -> None:
        if hasattr(self, '_winner_shown') and self._winner_shown:
            return
        
        self._winner_shown = True

        stats_file = "game_stats.json"
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except FileNotFoundError:
            stats = {"white_wins": 0, "red_wins": 0}
        
        if "белые" in winner:
            stats["white_wins"] += 1
        elif "красные" in winner:
            stats["red_wins"] += 1
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f)

        winner_window = tk.Toplevel(self.root)
        winner_window.title("Победа!")
        winner_window.transient(self.root)
        winner_window.grab_set()

        window_width: int = 300
        window_height: int = 150

        screen_width: int = winner_window.winfo_screenwidth()
        screen_height: int = winner_window.winfo_screenheight()

        center_x: int = int(screen_width/2 - window_width/2)
        center_y: int = int(screen_height/2 - window_height/2)

        winner_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        winner_window.resizable(False, False)

        frame = tk.Frame(winner_window, padx=20, pady=20)
        frame.pack(expand=True, fill='both')

        label = tk.Label(
            frame, 
            text=f"Победили {winner}!", 
            font=("Arial", 16, "bold")
        )
        label.pack(pady=10)

        button = tk.Button(
            frame, 
            text="Новая игра",
            font=("Arial", 12),
            width=15,
            command=lambda: [winner_window.destroy(), self._restart_game()]
        )
        button.pack(pady=10)

        if hasattr(self, 'bot') and hasattr(self.bot, 'learn_from_outcome'):
            winner_color = "RED" if "красные" in winner else "WHITE"
            self.bot.learn_from_outcome(self.get_board_state(), winner_color)

    def _make_king(self, row: int, col: int) -> None:
        piece = self.board[row][col]
        if not piece["is_king"]:
            piece["is_king"] = True
            x, y = col * CELL_SIZE, row * CELL_SIZE
            piece["crown"] = self.canvas.create_oval(
                x + 25, y + 25,
                x + CELL_SIZE - 25, y + CELL_SIZE - 25,
                fill=CROWN_COLOR
            )

    def _change_turn(self) -> None:

        if self.current_turn == "WHITE":
            self.current_turn = "RED"
            self.current_player_text = "красные"
        else:
            self.current_turn = "WHITE"
            self.current_player_text = "белые"
        
        self.moved_this_turn = False
        self.turn_label.config(text=f"Ходят {self.current_player_text}")
        
        # Проверяем пат после смены хода
        if not self.game_over:
            self._check_winner()

        if self.current_turn == "RED":
            self._schedule_bot_move()
        
        if not self.game_over and self.current_turn == "RED":
            self._schedule_bot_move()

    def _update_piece_position(self, row: int, col: int) -> None:
        x, y = col * CELL_SIZE, row * CELL_SIZE
        self.canvas.coords(
            self.selected_piece["piece"], 
            x + 10, y + 10, 
            x + CELL_SIZE - 10, y + CELL_SIZE - 10
        )
        
        if self.selected_piece["crown"]:
            self.canvas.coords(
                self.selected_piece["crown"],
                x + 25, y + 25,
                x + CELL_SIZE - 25, y + CELL_SIZE - 25
            )

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        menubar.add_command(label="Новая игра", command=self._restart_game)
        menubar.add_command(label="Правила", command=self._show_rules)
        menubar.add_command(label="Статистика", command=self._show_statistics)

        menubar.add_command(label="Обучить бота", command=self._show_train_dialog)

    def _restart_game(self) -> None:
        if messagebox.askyesno("Новая игра", "Вы уверены, что хотите начать новую игру?"):
            self.game_over = False
            self._winner_shown = False
            self.bot_thinking = False
            self.canvas.delete("all")
            self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
            self.moves_text.delete(1.0, tk.END)
            self.selected_piece = None
            self.start_pos = None
            self.current_turn = "WHITE"
            self.current_player_text = "белые"
            self.red_pieces = 8
            self.white_pieces = 8
            self.moved_this_turn = False
            self._create_labels()
            self._init_board()
            self._place_pieces()
            self._bind_events()

    def _on_closing(self) -> None:
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.root.quit()
            self.root.destroy()

    def _show_rules(self) -> None:
        rules_window = tk.Toplevel(self.root)
        rules_window.title("Правила игры")
        rules_window.transient(self.root)
        rules_window.grab_set()
        
        window_width = 600
        window_height = 400
        
        screen_width = rules_window.winfo_screenwidth()
        screen_height = rules_window.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        rules_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        rules_window.resizable(False, False)
        
        frame = tk.Frame(rules_window, padx=20, pady=20)
        frame.pack(expand=True, fill='both')
        
        rules_text = """Основные правила тайских шашек:

1. Простые шашки:
   - Ходят только по диагонали вперед на одну клетку
   - Бьют только вперед через одну клетку
   - После взятия шашка может продолжить бить, если есть такая возможность

2. Взятие обязательно:
   - При возможности взятия нескольких шашек, надо взять максимальное количество

3. Дамка (коронованная шашка):
   - Ходит на любое количество клеток по диагонали вперед и назад
   - При взятии должна встать сразу после взятой шашки

4. Шашка становится дамкой, достигнув последней горизонтали.
   После этого ход сразу переходит к другому игроку.

5. Игра заканчивается когда:
   - Все шашки противника побиты
   - У противника нет возможности хода (пат)
   
6. Первыми ходят белые шашки."""
        
        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Arial", 12), height=15)
        text_widget.pack(expand=True, fill='both')
        text_widget.insert(tk.END, rules_text)
        text_widget.config(state='disabled')
        
        button = tk.Button(
            frame,
            text="Закрыть",
            font=("Arial", 12),
            command=rules_window.destroy
        )
        button.pack(pady=10)

    def _show_statistics(self) -> None:
        stats_file = "game_stats.json"
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except FileNotFoundError:
            stats = {"white_wins": 0, "red_wins": 0}
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Статистика игр")
        stats_window.transient(self.root)
        stats_window.grab_set()
        
        window_width = 300
        window_height = 200
        
        screen_width = stats_window.winfo_screenwidth()
        screen_height = stats_window.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        stats_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        stats_window.resizable(False, False)
        
        frame = tk.Frame(stats_window, padx=20, pady=20)
        frame.pack(expand=True, fill='both')
        
        tk.Label(
            frame,
            text="Статистика побед:",
            font=("Arial", 14, "bold")
        ).pack(pady=10)
        
        tk.Label(
            frame,
            text=f"Белые: {stats['white_wins']}",
            font=("Arial", 12)
        ).pack(pady=5)
        
        tk.Label(
            frame,
            text=f"Красные: {stats['red_wins']}",
            font=("Arial", 12)
        ).pack(pady=5)
        
        button = tk.Button(
            frame,
            text="Закрыть",
            font=("Arial", 12),
            command=stats_window.destroy
        )
        button.pack(pady=10)

#========================================================================================================================================================================================================
#========================================================================================================================================================================================================
    def self_train_bot(self, games: int = 1000, save_interval: int = 100):
        """
        Запускает самообучение бота (бот играет сам с собой)
        
        Args:
            games: количество игр для обучения
            save_interval: сохранять Q-таблицу каждые N игр
        """
        from tkinter import messagebox
        
        # Сохраняем исходный режим
        original_mode = self.game_mode
        original_bot_color = self.bot.color
        
        # Переключаем в режим обучения
        self.game_mode = "self_train"
        self.bot_thinking = False  # Отключаем проверки на "думает"
        
        # Создаём второго бота (для игры против)
        second_bot = BotPlayer(game_instance=self)
        second_bot.color = "WHITE"
        
        # Можно загрузить ту же Q-таблицу для ускорения
        if hasattr(second_bot, 'q_table'):
            second_bot.q_table = self.bot.q_table
        
        # Параметры для статистики
        red_wins = 0
        white_wins = 0
        stalemates = 0
        
        print(f"Начинаем самообучение на {games} игр...")
        print(f"Параметры: epsilon={self.bot.epsilon}, alpha={self.bot.alpha}, gamma={self.bot.gamma}")
        
        for game_num in range(1, games + 1):
            # Перезапускаем игру
            self._restart_game_quiet()  # Тихий перезапуск без вопросов
            
            # Устанавливаем цвет ботов
            red_bot = self.bot  # RED
            red_bot.color = "RED"
            white_bot = second_bot
            white_bot.color = "WHITE"
            
            # Обнуляем трекинг обучения
            red_bot.last_state = None
            red_bot.last_action = None
            white_bot.last_state = None
            white_bot.last_action = None
            
            # Играем партию
            move_count = 0
            max_moves = 200  # Защита от бесконечных игр
            
            while move_count < max_moves:
                current_bot = red_bot if self.current_turn == "RED" else white_bot
                
                # Получаем состояние до хода
                before_state = current_bot.get_state_hash(self.get_board_state())
                
                # Получаем ход
                move = current_bot.get_move()
                
                if move is None:
                    # Нет ходов - проигрыш
                    loser = self.current_turn
                    break
                
                # Сохраняем действие
                action_hash = current_bot.get_action_hash(move[0], move[1])
                
                # Выполняем ход
                start_pos, end_pos = move
                is_capture = abs(end_pos[0] - start_pos[0]) == 2 and abs(end_pos[1] - start_pos[1]) == 2
                
                # Симулируем результат (без отрисовки)
                old_board = copy.deepcopy(self.get_board_state())
                self._execute_bot_move_fast(start_pos, end_pos, is_capture)
                
                # Вычисляем награду
                new_board = self.get_board_state()
                reward = current_bot.get_reward(
                    new_board, 
                    True, 
                    is_capture, 
                    is_capture,  # piece_captured
                    self._is_king_made(old_board, new_board, end_pos)
                )
                
                # Обучаем бота
                current_bot.learn_from_move(before_state, action_hash, new_board, reward)
                
                move_count += 1
            
            # Игра закончилась - финальное обучение
            winner = self._determine_winner()
            
            if winner == "RED":
                red_wins += 1
                red_bot.learn_from_outcome(self.get_board_state(), "RED")
                white_bot.learn_from_outcome(self.get_board_state(), "RED")
            elif winner == "WHITE":
                white_wins += 1
                red_bot.learn_from_outcome(self.get_board_state(), "WHITE")
                white_bot.learn_from_outcome(self.get_board_state(), "WHITE")
            else:
                stalemates += 1
            
            # Сохраняем прогресс
            if game_num % save_interval == 0:
                red_bot.save_q_table()
                win_rate = (red_wins + white_wins) / game_num * 100
                print(f"Игра {game_num}/{games} | Красные: {red_wins} | Белые: {white_wins} | Паты: {stalemates} | WinRate: {win_rate:.1f}%")
                print(f"Q-таблица: {len(red_bot.q_table)} состояний")
        
        # Финальное сохранение
        self.bot.save_q_table()
        
        # Восстанавливаем режим
        self.game_mode = original_mode
        self.bot.color = original_bot_color
        
        print(f"\nОбучение завершено!")
        print(f"Итоговая статистика за {games} игр:")
        print(f"Красные (бот): {red_wins} побед ({red_wins/games*100:.1f}%)")
        print(f"Белые (бот): {white_wins} побед ({white_wins/games*100:.1f}%)")
        print(f"Паты: {stalemates} ({stalemates/games*100:.1f}%)")
        print(f"Q-таблица сохранена в {self.bot.q_table_file}")
        print(f"Всего изучено состояний: {len(self.bot.q_table)}")
        
        # Показываем сообщение пользователю
        messagebox.showinfo("Обучение завершено", 
                        f"Бот обучился на {games} играх!\n"
                        f"Победы: {red_wins + white_wins}\n"
                        f"Всего состояний: {len(self.bot.q_table)}")
        
        self._restart_game()  # Перезапускаем для обычной игры
        
    def _restart_game_quiet(self):
        """Тихий перезапуск игры (без вопросов)"""
        self.game_over = False
        self._winner_shown = False
        self.canvas.delete("all")
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.moves_text.delete(1.0, tk.END)
        self.selected_piece = None
        self.start_pos = None
        self.current_turn = "WHITE"
        self.current_player_text = "белые"
        self.red_pieces = 8
        self.white_pieces = 8
        self.moved_this_turn = False
        self._init_board()
        self._place_pieces()
        
    def _execute_bot_move_fast(self, start_pos: Position, end_pos: Position, is_capture: bool):
        """Быстрое выполнение хода бота без анимации для самообучения"""
        if self.game_over:
            return

        old_row, old_col = start_pos
        new_row, new_col = end_pos
        
        # Удаляем срубленную фигуру
        if is_capture:
            dr = 1 if new_row > old_row else -1
            dc = 1 if new_col > old_col else -1
            curr_row, curr_col = old_row + dr, old_col + dc
            
            while curr_row != new_row or curr_col != new_col:
                if self.board[curr_row][curr_col]:
                    self._remove_piece_fast(curr_row, curr_col)
                    break
                curr_row += dr
                curr_col += dc
        
        # Перемещаем фигуру
        piece = self.board[old_row][old_col]
        self.board[new_row][new_col] = piece
        self.board[old_row][old_col] = None
        
        # Проверяем превращение в дамку
        if piece and not piece["is_king"]:
            if (new_row == 0 and piece["color"] == WHITE_PIECE_COLOR) or \
                (new_row == BOARD_SIZE - 1 and piece["color"] == RED_PIECE_COLOR):
                piece["is_king"] = True
        
        # Меняем ход
        self._change_turn_fast()
        
    def _remove_piece_fast(self, row: int, col: int):
        """Быстрое удаление фигуры без обновления canvas"""
        piece = self.board[row][col]
        if piece:
            self.board[row][col] = None
            if piece["color"] == RED_PIECE_COLOR:
                self.red_pieces -= 1
            else:
                self.white_pieces -= 1
        
    def _change_turn_fast(self):
        """Быстрая смена хода"""
        if self.current_turn == "WHITE":
            self.current_turn = "RED"
        else:
            self.current_turn = "WHITE"
        self.moved_this_turn = False
        
    def _is_king_made(self, old_board, new_board, end_pos: Position) -> bool:
        """Проверяет, стала ли шашка дамкой"""
        row, col = end_pos
        piece = new_board[row][col]
        if piece and not piece["is_king"]:
            return False
        # Если в новой доске дамка, а в старой - нет
        old_piece = old_board[row][col] if old_board[row][col] else None
        if old_piece:
            return not old_piece.get("is_king", False) and piece.get("is_king", False)
        return False
        
    def _determine_winner(self) -> Optional[str]:
        """Определяет победителя"""
        if self.red_pieces == 0:
            return "WHITE"
        elif self.white_pieces == 0:
            return "RED"
        
        # Проверка на пат
        current_color = RED_PIECE_COLOR if self.current_turn == "RED" else WHITE_PIECE_COLOR
        has_moves = False
        
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece and piece["color"] == current_color:
                    if self._has_any_move(row, col):
                        has_moves = True
                        break
            if has_moves:
                break
        
        if not has_moves:
            return "WHITE" if self.current_turn == "RED" else "RED"
        
        return None

    def _has_any_move(self, row: int, col: int) -> bool:
        """Проверяет, есть ли у фигуры ходы"""
        piece = self.board[row][col]
        if not piece:
            return False
        
        # Проверяем взятия
        if self.bot._has_capture_from_position(self.board, row, col):
            return True
        
        # Проверяем обычные ходы
        if piece["is_king"]:
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    if not self.board[new_row][new_col]:
                        return True
        else:
            if piece["color"] == WHITE_PIECE_COLOR:
                directions = [(-1, -1), (-1, 1)]
            else:
                directions = [(1, -1), (1, 1)]
            
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    if not self.board[new_row][new_col]:
                        return True
        
        return False
    
    def _show_train_dialog(self):
        """Показывает диалог для настройки самообучения"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Обучение бота")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем окно
        window_width, window_height = 500, 450
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        dialog.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        dialog.resizable(False, False)
        
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(expand=True, fill='both')
        
        tk.Label(frame, text="Самообучение бота", font=("Arial", 14, "bold")).pack(pady=10)
        
        tk.Label(frame, text="Количество игр:").pack(pady=(20, 5))
        games_var = tk.StringVar(value="1000")
        games_entry = tk.Entry(frame, textvariable=games_var, font=("Arial", 12), width=15)
        games_entry.pack()
        
        tk.Label(frame, text="Параметры обучения:", font=("Arial", 11, "bold")).pack(pady=(20, 5))
        params_frame = tk.Frame(frame)
        params_frame.pack()
        
        tk.Label(params_frame, text="ε (epsilon):", width=12, anchor='w').grid(row=0, column=0, pady=2)
        epsilon_var = tk.StringVar(value=str(self.bot.epsilon))
        epsilon_entry = tk.Entry(params_frame, textvariable=epsilon_var, width=8)
        epsilon_entry.grid(row=0, column=1, pady=2)
        
        tk.Label(params_frame, text="α (alpha):", width=12, anchor='w').grid(row=1, column=0, pady=2)
        alpha_var = tk.StringVar(value=str(self.bot.alpha))
        alpha_entry = tk.Entry(params_frame, textvariable=alpha_var, width=8)
        alpha_entry.grid(row=1, column=1, pady=2)
        
        tk.Label(frame, text="Внимание! Обучение может занять\nнесколько часов!", 
                font=("Arial", 10), fg="red").pack(pady=20)
        
        button_frame = tk.Frame(frame)
        button_frame.pack(pady=10)
    
        def start_training():
            try:
                games = int(games_var.get())
                epsilon = float(epsilon_var.get())
                alpha = float(alpha_var.get())
                
                # Временно меняем параметры
                old_epsilon = self.bot.epsilon
                old_alpha = self.bot.alpha
                
                self.bot.epsilon = epsilon
                self.bot.alpha = alpha
                
                dialog.destroy()
                
                # Запускаем обучение в отдельном потоке? Нет, tkinter не любит потоки
                # Просто запускаем с возможностью прерывания
                self.root.after(100, lambda: self.self_train_bot(games))
                
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректные числа!")
        
        confirm_button = tk.Button(
            button_frame, 
            text="Начать обучение",  
            font=("Arial", 12, "bold"),
            command=start_training,     
            bg="#4CAF50",               
            fg="white",                 
            padx=20,
            pady=5
        )
        confirm_button.pack()
    

        cancel_button = tk.Button(
            button_frame,
            text="Отмена",
            font=("Arial", 12),
            command=dialog.destroy,
            padx=20,
            pady=5
        )
        cancel_button.pack(pady=5)

class LoginForm:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Авторизация")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        window_width: int = 400
        window_height: int = 300
        
        screen_width: int = self.root.winfo_screenwidth()
        screen_height: int = self.root.winfo_screenheight()
        
        center_x: int = int(screen_width/2 - window_width/2)
        center_y: int = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.resizable(False, False)
        
        self.main_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')
        
        self._create_widgets()
        
        self.users_file: str = "users.json"
        
        self._load_users()

    def _create_widgets(self) -> None:
        title_label = tk.Label(
            self.main_frame, 
            text="Авторизация", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        login_frame = tk.Frame(self.main_frame)
        login_frame.pack(fill='x', pady=5)
        
        tk.Label(
            login_frame, 
            text="Логин:", 
            font=("Arial", 12)
        ).pack(side='left', padx=5)
        
        self.login_entry = tk.Entry(
            login_frame, 
            font=("Arial", 12),
            width=25
        )
        self.login_entry.pack(side='left', padx=5)
        
        password_frame = tk.Frame(self.main_frame)
        password_frame.pack(fill='x', pady=5)
        
        tk.Label(
            password_frame, 
            text="Пароль:", 
            font=("Arial", 12)
        ).pack(side='left', padx=5)
        
        self.password_entry = tk.Entry(
            password_frame, 
            show="*",
            font=("Arial", 12),
            width=25
        )
        self.password_entry.pack(side='left', padx=5)
        
        buttons_frame = tk.Frame(self.main_frame)
        buttons_frame.pack(pady=20)
        
        tk.Button(
            buttons_frame, 
            text="Войти",
            font=("Arial", 12),
            width=15,
            command=self._login
        ).pack(side='left', padx=10)
        
        tk.Button(
            buttons_frame, 
            text="Регистрация",
            font=("Arial", 12),
            width=15,
            command=self._show_register_window
        ).pack(side='left', padx=10)

    def _load_users(self) -> None:
        self.users: Dict[str, str] = {}
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _login(self) -> None:
        login: str = self.login_entry.get()
        password: str = self.password_entry.get()
        
        if not login or not password:
            messagebox.showerror("Ошибка", "Заполните все поля!")
            return
        
        hashed_password: str = self._hash_password(password)
        
        if login in self.users and self.users[login] == hashed_password:
            self.root.destroy()
            self._start_game()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def _start_game(self) -> None:
        game_root = tk.Tk()
        game = MakYek(game_root)
        game_root.mainloop()

    def run(self) -> None:
        self.root.mainloop()

    def _show_register_window(self) -> None:
        self.root.destroy()
        self.register_window = tk.Tk()
        self.register_window.title("Регистрация")
        self.register_window.protocol("WM_DELETE_WINDOW", self._show_login_window)
        
        window_width: int = 600
        window_height: int = 600
        screen_width: int = self.register_window.winfo_screenwidth()
        screen_height: int = self.register_window.winfo_screenheight()
        center_x: int = int(screen_width/2 - window_width/2)
        center_y: int = int(screen_height/2 - window_height/2)
        self.register_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        register_frame = tk.Frame(self.register_window, padx=40, pady=40)
        register_frame.pack(expand=True, fill='both')
        
        tk.Label(
            register_frame,
            text="Регистрация нового пользователя",
            font=("Arial", 16, "bold")
        ).pack(pady=20)
        
        fields_frame = tk.Frame(register_frame)
        fields_frame.pack(pady=20)
        
        tk.Label(fields_frame, text="Логин:", font=("Arial", 12)).pack(pady=5)
        self.reg_login = tk.Entry(fields_frame, font=("Arial", 12), width=35)
        self.reg_login.pack(pady=10)
        
        tk.Label(fields_frame, text="Пароль:", font=("Arial", 12)).pack(pady=5)
        self.reg_password = tk.Entry(fields_frame, show="*", font=("Arial", 12), width=35)
        self.reg_password.pack(pady=10)
        
        tk.Label(fields_frame, text="Повторите пароль:", font=("Arial", 12)).pack(pady=5)
        self.reg_password_confirm = tk.Entry(fields_frame, show="*", font=("Arial", 12), width=35)
        self.reg_password_confirm.pack(pady=10)
        
        buttons_frame = tk.Frame(register_frame)
        buttons_frame.pack(pady=30, side='bottom')
        
        tk.Button(
            buttons_frame,
            text="Зарегистрироваться",
            font=("Arial", 12),
            width=25,
            command=self._register
        ).pack(side='left', padx=20)
        
        tk.Button(
            buttons_frame,
            text="Вернуться к входу",
            font=("Arial", 12),
            width=25,
            command=self._show_login_window
        ).pack(side='left', padx=20)

    def _show_login_window(self) -> None:
        self.register_window.destroy()
        self.__init__()
        self.run()

    def _register(self) -> None:
        login: str = self.reg_login.get().strip()
        password: str = self.reg_password.get()
        password_confirm: str = self.reg_password_confirm.get()
        
        if not login or not password or not password_confirm:
            messagebox.showerror("Ошибка", "Заполните все поля!")
            return
            
        if len(login) < 3:
            messagebox.showerror("Ошибка", "Логин должен содержать минимум 3 символа!")
            return
            
        if not login.isalnum():
            messagebox.showerror("Ошибка", "Логин может содержать только буквы и цифры!")
            return
            
        if login in self.users:
            messagebox.showerror("Ошибка", "Пользоваель с таким логином уже существует!")
            return
            
        if password != password_confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают!")
            return
            
        if len(password) < 4:
            messagebox.showerror("Ошибка", "Пароль должен содержать минимум 4 символа!")
            return
        
        self.users[login] = self._hash_password(password)
        
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)
        
        messagebox.showinfo("Успех", "Регистрация успешно завершена!")
        self._show_login_window()

    def _on_closing(self) -> None:
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.root.quit()
            self.root.destroy()


if __name__ == "__main__":
    login_form = LoginForm()
    login_form.run()