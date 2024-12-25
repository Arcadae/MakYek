import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Optional, Tuple, Set, Any, TypeAlias, NotRequired, TypedDict, Literal
import hashlib
import json
import os

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
        self.root = root
        self.root.title("Тайские шашки")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
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
        self.canvas.bind("<ButtonPress-1>", self._on_piece_click)
        self.canvas.bind("<ButtonRelease-1>", self._on_drop)

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
            winner = "белые" if self.current_turn == "RED" else "красные"
            self._show_winner(f"{winner} (пат)")

    def _show_winner(self, winner: str) -> None:
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
        self._check_winner()

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

    def _restart_game(self) -> None:
        if messagebox.askyesno("Новая игра", "Вы уверены, что хотите начать новую игру?"):
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
