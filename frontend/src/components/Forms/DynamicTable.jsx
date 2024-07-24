import React, { useEffect } from 'react';
import { Table } from 'react-bootstrap';
import { BiEditAlt, BiTrashAlt } from 'react-icons/bi';
import axios from 'axios';

const DynamicTable = ({ apiUrl, data, fields, setData, setCurrentDataIndex}) => {

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await axios.get(apiUrl);
      setData(response.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const handleEdit = (index) => {
      setCurrentDataIndex(index); // Set the current data to be edited
  };
  
  const handleDelete = async (id) => {
    const confirmDelete = window.confirm('Are you sure you want to delete this item?');
    if (confirmDelete) {
      try {
        await axios.delete(`${apiUrl}/${id}`);
        fetchData(); // Refresh data after deletion
      } catch (error) {
        console.error('Error deleting data:', error);
      }
    }
  };
  


  return (
    <div className="card">
      <div className="card-body">
        <h5 className="card-title">All Data</h5>

        <Table responsive className="table table-hover">
          <thead>
            <tr>
              {fields.map((field) => (
                <th key={field.id}>{field.label}</th>
              ))}
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr key={index}>
                {fields.map((field) => (
                  <td key={field.id}>{item[field.id]}</td>
                ))}
                <td>
                  <BiEditAlt className='icon' onClick={() => handleEdit(index)} />
                  <BiTrashAlt className='icon' onClick={() => handleDelete(index)} />
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
};

export default DynamicTable;
