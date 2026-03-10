open Cil
open Flatten
open Virtualize
open Opaque

let () =
  Printexc.record_backtrace true;
  Cil.initCIL ();

  let input = ref "" in
  let output = ref "" in

  let flag_flatten = ref false in
  let flag_virtualize = ref false in
  let flag_opaque = ref false in

  let pos_args = ref [] in

  Arg.parse
    [
      ("-flatten", Arg.Set flag_flatten, "Run flatten pass");
      ("-virtualize", Arg.Set flag_virtualize, "Run virtualization pass");
      ("-opaque", Arg.Set flag_opaque, "Run opaque/MBA pass");
    ]
    (fun s -> pos_args := !pos_args @ [s])
    "usage: tool input output -flatten|-opaque|-virtualize";

  (match !pos_args with
  | [i; o] ->
      input := i;
      output := o
  | _ ->
      prerr_endline "Error: need input and output file";
      exit 1
  );

  let mode_count =
    (if !flag_flatten then 1 else 0) +
    (if !flag_opaque then 1 else 0) +
    (if !flag_virtualize then 1 else 0)
  in

  if mode_count <> 1 then begin
    prerr_endline "Error: choose exactly one mode";
    exit 1
  end;

  let file = Frontc.parse !input () in

  if !flag_flatten then begin
    Flatten.run file;
    let oc = open_out !output in
    Cil.dumpFile defaultCilPrinter oc !output file;
    close_out oc
  end;

  if !flag_opaque then begin
    Opaque.run file;
    let oc = open_out !output in
    Cil.dumpFile defaultCilPrinter oc !output file;
    close_out oc
  end;

  if !flag_virtualize then begin
    Virtualize.run ~output:!output file;
  end;
