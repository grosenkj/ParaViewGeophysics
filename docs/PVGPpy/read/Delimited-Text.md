!!! info "Purpose"
    The main advantage of having this reader and using it over the default delimited text reader is that we can specify to use tab (`\t`) delimiters and that we deliver to the users of this repo a delimited text reader that they manipulate to work for their file format needs.

## About this Reader
This reader will take in any delimited text file and make a vtkTable from it. This is not much different than the default .txt or .csv reader in ParaView, however it gives us room to use our own extensions and a little more flexibility in the structure of the files we import.

## Down the Pipeline
- [Table to Uniform Grid](../filt/Table-to-Uniform-Grid.md)
- [Reshape Table](../filt/Reshape-Table.md)
- [Table to Points](https://www.paraview.org/Wiki/ParaView/Users_Guide/List_of_filters#Table_To_Points)
- [Table to Structured Grid](https://www.paraview.org/Wiki/ParaView/Users_Guide/List_of_filters#Table_To_Structured_Grid)
- [Normalize Array](../filt/Normalize-Array.md)

-----

## Code Docs

{def:PVGPpy.read.delimitedText}
