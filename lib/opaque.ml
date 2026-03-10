open Cil
open Unix

let loc = Cil.locUnknown


let mba_script = ref "lib/mba.py"
let python_cmd = ref "python3"
let target_state_prefix = "__state"


let trim (s : string) : string =
  let is_space = function ' ' | '\n' | '\r' | '\t' -> true | _ -> false in
  let len = String.length s in
  let i = ref 0 in
  while !i < len && is_space s.[!i] do incr i done;
  let j = ref (len - 1) in
  while !j >= !i && is_space s.[!j] do decr j done;
  if !j < !i then "" else String.sub s !i (!j - !i + 1)

let u32_of_int64 (i : int64) : int64 =
  Int64.logand i 0xFFFFFFFFL

let run_mba (x_u32 : int64) : string option =
  let cmd = Printf.sprintf "%s %s %s 2>/dev/null" !python_cmd !mba_script (Int64.to_string x_u32) in
  let env = Unix.environment () in
  let (stdout_ch, stdin_ch, stderr_ch) = Unix.open_process_full cmd env in
  close_out stdin_ch; 
  let buf = Buffer.create 100000 in begin
  try
     while true do
       let line = input_line stdout_ch in
       Buffer.add_string buf line;
       Buffer.add_char buf '\n'
     done
  with End_of_file -> () end;
  let _ = begin try
      while true do ignore (input_line stderr_ch) done
    with End_of_file -> () end in
  let status = Unix.close_process_full (stdout_ch, stdin_ch, stderr_ch) in
  match status with
  | WEXITED 0 ->
      let out = trim (Buffer.contents buf) in
      if out = "" then None else Some out 
  | _ -> None


type token =
  | TInt of int64
  | TIdent of string
  | TOp of string
  | TLParen
  | TRParen
  | TEOF

let is_space = function ' ' | '\n' | '\r' | '\t' -> true | _ -> false

let is_digit c = c >= '0' && c <= '9'
let is_hex_digit c =
  (c >= '0' && c <= '9') ||
  (c >= 'a' && c <= 'f') ||
  (c >= 'A' && c <= 'F')

let is_ident_start c =
  (c >= 'a' && c <= 'z') ||
  (c >= 'A' && c <= 'Z') ||
  c = '_'

let is_ident_char c = is_ident_start c || is_digit c

let tokenize (s : string) : token list option =
  let len = String.length s in
  let i = ref 0 in
  let tokens = ref [] in
  let add t = tokens := t :: !tokens in
  let peek () = if !i < len then Some s.[!i] else None in
  let next () = let c = s.[!i] in incr i; c in
  let rec skip_spaces () =
    match peek () with
    | Some c when is_space c -> ignore (next ()); skip_spaces ()
    | _ -> ()
  in
  let rec skip_suffixes () =
    if !i < len then
      match s.[!i] with
      | 'u' | 'U' | 'l' | 'L' -> ignore (next ()); skip_suffixes ()
      | _ -> ()
  in

  let read_number () =
    let start = !i in
    let is_hex =
      if !i + 1 < len && s.[!i] = '0' && (s.[!i+1] = 'x' || s.[!i+1] = 'X')
      then true else false
    in
    if is_hex then begin
      ignore (next ()); ignore (next ());
      while !i < len && is_hex_digit s.[!i] do ignore (next ()) done
    end else begin
      while !i < len && is_digit s.[!i] do ignore (next ()) done
    end;
    let end_digits = !i in
    skip_suffixes ();
    let num_str = String.sub s start (end_digits - start) in
    try
      let v = Int64.of_string num_str in
      Some v
    with _ -> None
  in
  let read_ident () =
    let start = !i in
    ignore (next ());
    while !i < len && is_ident_char s.[!i] do ignore (next ()) done;
    String.sub s start (!i - start)
  in
  let read_op () =
    let two =
      if !i + 1 < len then String.sub s !i 2 else ""
    in
    let one = String.sub s !i 1 in
    let op =
      match two with
      | "||" | "&&" | "<<" | ">>" | "<=" | ">=" | "==" | "!=" -> Some two
      | _ ->
          match one with
          | "|" | "^" | "&" | "<" | ">" | "+" | "-" | "*" | "/" | "%" | "!" | "~" -> Some one
          | _ -> None
    in
    match op with
    | Some o ->
        i := !i + String.length o;
        Some o
    | None -> None
  in
  let rec loop () =
    skip_spaces ();
    match peek () with
    | None -> add TEOF; Some (List.rev !tokens)
    | Some '(' -> ignore (next ()); add TLParen; loop ()
    | Some ')' -> ignore (next ()); add TRParen; loop ()
    | Some c when is_digit c ->
        (match read_number () with
         | Some v -> add (TInt v); loop ()
         | None -> None)
    | Some c when is_ident_start c ->
        let id = read_ident () in
        add (TIdent id); loop ()
    | Some _ ->
        (match read_op () with
         | Some o -> add (TOp o); loop ()
         | None -> None)
  in
  loop ()

let prec_of = function
  | "||" -> 1
  | "&&" -> 2
  | "|"  -> 3
  | "^"  -> 4
  | "&"  -> 5
  | "==" | "!=" -> 6
  | "<" | "<=" | ">" | ">=" -> 7
  | "<<" | ">>" -> 8
  | "+" | "-" -> 9
  | "*" | "/" | "%" -> 10
  | _ -> 0

let binop_of = function
  | "+" -> PlusA
  | "-" -> MinusA
  | "*" -> Mult
  | "/" -> Div
  | "%" -> Mod
  | "<<" -> Shiftlt
  | ">>" -> Shiftrt
  | "&" -> BAnd
  | "^" -> BXor
  | "|" -> BOr
  | "&&" -> LAnd
  | "||" -> LOr
  | "==" -> Eq
  | "!=" -> Ne
  | "<" -> Lt
  | "<=" -> Le
  | ">" -> Gt
  | ">=" -> Ge
  | _ -> PlusA

let is_logic_or_cmp = function
  | LAnd | LOr | Eq | Ne | Lt | Le | Gt | Ge -> true
  | _ -> false

let parse_mba_expr (s : string) (a0 : varinfo) (a1 : varinfo) : exp option =
  match tokenize s with
  | None -> None
  | Some toks ->
      let toks = Array.of_list toks in
      let pos = ref 0 in
      let peek () = toks.(!pos) in
      let eat () = let t = toks.(!pos) in incr pos; t in
      let expect t =
        if peek () = t then ignore (eat ()) else raise Exit
      in
      let rec parse_expr min_prec =
        let lhs = parse_unary () in
        parse_bin_rhs lhs min_prec
      and parse_unary () =
        match peek () with
        | TOp "+" -> ignore (eat ()); parse_unary ()
        | TOp "-" -> ignore (eat ()); let e = parse_unary () in UnOp (Neg, e, uintType)
        | TOp "!" -> ignore (eat ()); let e = parse_unary () in UnOp (LNot, e, intType)
        | TOp "~" -> ignore (eat ()); let e = parse_unary () in UnOp (BNot, e, uintType)
        | _ -> parse_primary ()
      and parse_primary () =
        match eat () with
        | TInt i -> Const (CInt64 (i, IUInt, None))
        | TIdent id ->
            if id = "a0" then Lval (Var a0, NoOffset)
            else if id = "a1" then Lval (Var a1, NoOffset)
            else raise Exit
        | TLParen ->
            let e = parse_expr 0 in
            expect TRParen;
            e
        | _ -> raise Exit
      and parse_bin_rhs lhs min_prec =
        match peek () with
        | TOp op ->
            let prec = prec_of op in
            if prec < min_prec then lhs
            else begin
              ignore (eat ());
              let next_min = prec + 1 in
              let rhs = parse_expr next_min in
              let bop = binop_of op in
              let ty = if is_logic_or_cmp bop then intType else uintType in
              let lhs' = BinOp (bop, lhs, rhs, ty) in
              parse_bin_rhs lhs' min_prec
            end
        | _ -> lhs
      in
      try
        let e = parse_expr 0 in
        (match peek () with
         | TEOF -> Some e
         | _ -> None)
      with Exit -> None


let rand_vi_cache : varinfo option ref = ref None

let find_or_create_rand (file : file) : varinfo =
  match !rand_vi_cache with
  | Some vi -> vi
  | None ->
      let t = TFun(intType, Some [], false, []) in
      let vi = Cil.findOrCreateFunc file "rand" t in
      rand_vi_cache := Some vi;
      vi

let mk_rand_call (rand_vi : varinfo) (dst : varinfo) : instr =
  Call (Some (Var dst, NoOffset), Lval (Var rand_vi, NoOffset), [], loc)


let mba_exp_for_const (x_u32 : int64) (a0 : varinfo) (a1 : varinfo) : exp option =
  match run_mba x_u32 with
  | None -> None
  | Some s -> parse_mba_expr s a0 a1


class obfuscator (file : file) = object(self)
  inherit nopCilVisitor

  val mutable cur_a0 : varinfo option = None
  val mutable cur_a1 : varinfo option = None

  method private ensure_locals (fd : fundec) : unit =
    let a0 = makeTempVar fd ~name:"__a0" uintType in
    let a1 = makeTempVar fd ~name:"__a1" uintType in
    cur_a0 <- Some a0;
    cur_a1 <- Some a1

  method! vfunc (fd : fundec) =
    self#ensure_locals fd;
    DoChildren

  method private replace_first_const (e : exp) (a0 : varinfo) (a1 : varinfo) : (bool * exp) =
    let replaced = ref false in
    let v = object
      inherit nopCilVisitor
      method! vexpr ex =
        if !replaced then SkipChildren
        else
          match ex with
          | Const (CInt64 (i, _, _)) ->
              let u32 = u32_of_int64 i in
              (match mba_exp_for_const u32 a0 a1 with
               | Some mba_e ->
                   replaced := true;
                   ChangeTo mba_e
               | None -> SkipChildren)
          | _ -> DoChildren
    end in
    let e' = visitCilExpr (v :> cilVisitor) e in
    (!replaced, e')

  method private maybe_obfuscate_instr
      (rand_vi : varinfo)
      (a0 : varinfo)
      (a1 : varinfo)
      (i : instr) : instr list =
    match i with
    | Set ((Var vi, NoOffset), e, l)
      when String.length vi.vname >= String.length target_state_prefix
        && String.sub vi.vname 0 (String.length target_state_prefix) = target_state_prefix ->
        let (did, e') = self#replace_first_const e a0 a1 in
        if did then
          [ mk_rand_call rand_vi a0;
            mk_rand_call rand_vi a1;
            Set ((Var vi, NoOffset), e', l) ]
        else
          [i]
    | _ -> [i]

  method private rewrite_instrs (il : instr list) (a0 : varinfo) (a1 : varinfo) : instr list =
    let rand_vi = find_or_create_rand file in
    let rec loop acc = function
      | [] -> List.rev acc
      | i :: tl ->
          let out = self#maybe_obfuscate_instr rand_vi a0 a1 i in
          let acc' = List.fold_left (fun a x -> x :: a) acc (List.rev out) in
          loop acc' tl
    in
    loop [] il

  method! vstmt (s : stmt) =
    match s.skind, cur_a0, cur_a1 with
    | Instr il, Some a0, Some a1 ->
        let il' = self#rewrite_instrs il a0 a1 in
        if il' == il then DoChildren
        else
          let ns = mkStmt (Instr il') in
          ns.labels <- s.labels; 
          ChangeTo ns
    | _ -> DoChildren
end

let run (file : file) : unit =
  visitCilFileSameGlobals (new obfuscator file) file
